import os
import requests
import argparse
from bs4 import BeautifulSoup
from io import BytesIO
from typing import Union
import xml.etree.ElementTree as ET
from tqdm import tqdm
from urllib.parse import urlparse, parse_qs
from db import db
from .stats_utils import get_stats, calculate_stats_diff, print_detailed_summary

def get_name_href(soup: BeautifulSoup):
    # Find all the xmls on the page content
    name_href_list = []
    for row in soup.find_all("tr"):
        cells = row.find_all("td")
        if len(cells) < 2:
            continue # skip malformed rows
        
        # First <td> = legislature name
        name = cells[0].get_text(strip=True)
        
        # Second <td> = contains <a> link
        a_tag = cells[1].find("a", href=True)
        if not a_tag:
            continue
        
        href = a_tag["href"]
        name_href_list.append((name,href))

    name_href_list = name_href_list[::-1]
    return name_href_list

def get_xml(name_href: tuple, output_dir: str, save_xml: bool=False):
    name = name_href[0]
    href = name_href[1]

    filename = href.split('=')[-1]
    filepath = f"{output_dir}/{filename}"
    parts = filename.split("data_")[-1].replace(".xml","").split("_")
    legislatura = int(parts[0])
    num = 0
    if len(parts) == 2:
        num = int(parts[1])

    # Download the XML content
    xml_response = requests.get(href)
    xml_response.raise_for_status()
    xml_content = xml_response.content
    
    # Create xml_info dictionary for update
    xml_info = {
        'legislatura': legislatura,
        'num': num,
        'name': name,
        'xml_url': href,
        'xml_filepath': filepath        
    }

    if save_xml:
        with open(filepath, "wb") as f:
            f.write(xml_content)

    return xml_info, xml_content

def get_multiple_sesion_info(xml_file: Union[str, bytes], sesion_type: str):
    if isinstance(xml_file, bytes):
        xml_file = BytesIO(xml_file)
    
    tree = ET.parse(xml_file)
    root = tree.getroot()

    tag_list = [
        "num_sesion",
        "fecha_inicio",
        "hora_inicio",
        "fecha_fin",
        "hora_fin",
        "diario_link"
    ]
    sesion_list = []
    for xml_sesion in root.findall(f".//sesiones_{sesion_type}"):
        sesion_info = {}

        # Add sesion header info
        for tag in tag_list:
            sesion_info[tag] = xml_sesion.findtext(f".//sesiones_{sesion_type}_{tag}", default="").strip()

        fecha_inicio = sesion_info.get("fecha_inicio")
        fecha_fin = sesion_info.get("fecha_fin")
        hora_inicio = sesion_info.get("hora_inicio")
        hora_fin = sesion_info.get("hora_fin")
        start_datetime = ""
        end_datetime = ""
        if fecha_inicio:
            di,mi,yi = fecha_inicio.split(".")
            start_datetime = f"{yi}-{mi}-{di}T{hora_inicio}"
        if fecha_fin:
            df,mf,yf = fecha_fin.split(".")
            end_datetime = f"{yf}-{mf}-{df}T{hora_fin}"

        # Get stream and m3u8 multiple links for each sesion
        streams = xml_sesion.findall(f".//sesiones_{sesion_type}_asunto_indice_link")
        stream_url_list = []
        m3u8_url_list = []
        m3u8_base_url = "https://bideoak.legebiltzarra.eus/bideoak/_definst_/mp4:"
        for s in streams:
            link = s.text.strip()
            
            parsed_url = urlparse(link)
            query_params = parse_qs(parsed_url.query)
            
            # Craft stream and m3u8 links (sometimes can be multiple link for sesion)
            streamlegealdia = query_params.get("streamlegealdia", [None])[0]
            streamorganoa = query_params.get("streamorganoa", [None])[0]
            streamdata = query_params.get("streamdata", [None])[0]
            streamname = query_params.get("streamname", [None])[0]
            
            stream_base_url = f"{parsed_url.scheme}://{parsed_url.netloc}{parsed_url.path}?streamlegealdia={streamlegealdia}&streamorganoa={streamorganoa}&streamdata={streamdata}"
            
            if streamname:
                stream_url = f"{stream_base_url}&streamname={streamname}&streamdbstart=00:00" 
                m3u8_url = f"{m3u8_base_url}{streamlegealdia}/{streamorganoa}/{streamdata}/{streamname}.mp4/playlist.m3u8" 
            else:
                stream_url = f"{stream_base_url}&streamdbstart={start_datetime}"
                m3u8_url = f"{m3u8_base_url}{streamlegealdia}/{streamorganoa}/{streamdata}/{streamdata}{streamorganoa}_01.mp4/playlist.m3u8"
            
            if stream_url not in stream_url_list:
                stream_url_list.append(stream_url)
                
            if m3u8_url not in m3u8_url_list:
                m3u8_url_list.append(m3u8_url)

        sesion = {
            'num': int(sesion_info['num_sesion']), 
            'start_datetime': start_datetime,
            'end_datetime': end_datetime,
            'pdf_url': sesion_info['diario_link'],
            'stream_url_list': stream_url_list,
            'm3u8_url_list': m3u8_url_list
        }

        sesion_list.append(sesion)
    
    return sesion_list

def main(args):
    output_dir = args.output_dir
    pleno_url = args.pleno_url
    base_comisiones_url = args.base_comisiones_url

    # Initialize DB
    conn = db.get_conn(db_path=args.db_path)
    db.init_db(conn)

    ini_stats, ini_detailed_stats = get_stats(conn)

    if not args.only_stats:        
        print_detailed_summary(ini_stats, ini_detailed_stats, title="ACTUAL DATA")
        os.makedirs(output_dir, exist_ok=True)

        # Get page content for plenos
        response = requests.get(url=pleno_url)
        response.raise_for_status()  # Raise error if request fails
        soup = BeautifulSoup(response.content, "html.parser")

        # Extract 'name' and 'href' for .xml and loop over them
        name_href_list = get_name_href(soup)
        for name_href in tqdm(name_href_list, desc="Scraping Legislatura Metadata"):
            try:
                # Download the xml
                xml_info, xml_content = get_xml(name_href=name_href, output_dir=output_dir, save_xml=args.save_xml)

                # Create the url for the comisiones based on the current legislatura
                comisiones_url = f"{base_comisiones_url}{xml_info['legislatura']}"
                
                # 1. Legislatura
                legislatura_id = db.get_or_create_legislatura(
                    conn,
                    num=xml_info['legislatura'],
                    name=xml_info['name'],
                    pleno_url=pleno_url,
                    comisiones_url=comisiones_url
                )

                # Get all the pleno sesions from the xml
                sesion_list = get_multiple_sesion_info(xml_file=xml_content, sesion_type='pleno')

                # 2. Organo Pleno (num=0)
                organo_id = db.get_or_create_organo(
                    conn,
                    legislatura_id=legislatura_id,
                    num=xml_info['num'],
                    name="Sesiones Plenarias",
                    xml_url=xml_info['xml_url'],
                    xml_filepath=xml_info['xml_filepath']
                )
                
                for sesion in sesion_list:
                    # 3. Sesiones
                    sesion_id= db.get_or_create_sesion(
                        conn,
                        organo_id=organo_id,
                        num=sesion['num'],
                        start_datetime=sesion['start_datetime'],
                        end_datetime=sesion['end_datetime'],
                        pdf_url=sesion['pdf_url']
                    )

                    # 4 Media URLs
                    for stream_url, m3u8_url in zip(sesion['stream_url_list'], sesion['m3u8_url_list']):
                        db.upsert_media_info(
                            conn,
                            sesion_id=sesion_id,
                            stream_url=stream_url,
                            m3u8_url=m3u8_url
                        )
                
                # Get page content for comisiones
                c_response = requests.get(url=comisiones_url)
                c_response.raise_for_status()  # Raise error if request fails
                c_soup = BeautifulSoup(c_response.content, "html.parser")
                
                # Find all the xmls on the page content
                c_name_href_list = get_name_href(c_soup)
                for c_name_href in c_name_href_list:
                    try:
                        # Download the xml
                        xml_info, xml_content = get_xml(name_href=c_name_href, output_dir=output_dir, save_xml=args.save_xml)

                        # 1. Organo Comisiones
                        organo_id= db.get_or_create_organo(
                            conn,
                            legislatura_id=legislatura_id,
                            num=xml_info['num'],
                            name=xml_info['name'],
                            xml_url=xml_info['xml_url'],
                            xml_filepath=xml_info['xml_filepath']
                        )

                        # Get all the comision sesions from the xml
                        sesion_list = get_multiple_sesion_info(xml_file=xml_content, sesion_type='comision')

                        for sesion in sesion_list:
                            # 2. Sesiones
                            sesion_id= db.get_or_create_sesion(
                                conn,
                                organo_id=organo_id,
                                num=sesion['num'],
                                start_datetime=sesion['start_datetime'],
                                end_datetime=sesion['end_datetime'],
                                pdf_url=sesion['pdf_url']
                            )

                            # 3. Media URLs
                            for stream_url, m3u8_url in zip(sesion['stream_url_list'], sesion['m3u8_url_list']):
                                db.upsert_media_info(
                                    conn,
                                    sesion_id=sesion_id,
                                    stream_url=stream_url,
                                    m3u8_url=m3u8_url
                                )

                    except ValueError as e:
                        print(f"Caught exception: {e}")

            except ValueError as e:
                print(f"Caught exception: {e}")

    fin_stats, fin_detailed_stats = get_stats(conn)

    if not args.only_stats:
        new_stats, new_detailed_stats = calculate_stats_diff(fin_stats, fin_detailed_stats, ini_stats, ini_detailed_stats)
        print_detailed_summary(new_stats, new_detailed_stats, title="NEW DATA")
    
    print_detailed_summary(fin_stats, fin_detailed_stats, title="TOTAL DATA")

    conn.close()
    
if __name__=="__main__":
    parser = argparse.ArgumentParser(description="Parliament Metadata Scraper",add_help=True)

    # Paths
    parser.add_argument("--db_path", type=str, required=True, help="(str): path to the SQLite DB", )
    parser.add_argument("--output_dir", type=str, default="./data", help="(str): path to the output directory for the xml files.")

    # Inputs
    parser.add_argument("--pleno_url", type=str, required=True, help="(str): url for the pleno xml files")
    parser.add_argument("--base_comisiones_url", type=str, required=True, help="(str): base url for the comisiones xml files")

    # Flags
    parser.add_argument("--save_xml", action='store_true', help="Activate only to save xml files on ./data")
    parser.add_argument("--only_stats", action='store_true', help="Activate only to print stats without downloading.")

    args = parser.parse_args()
    main(args)

