import os
import argparse
import requests
import subprocess
from db import db
from .stats_utils import get_stats, print_detailed_summary

def download_pdf(url: str, out_filepath: str):
    if url:      
        print(f" -> Downloading PDF: {url}", flush=True)
        try:
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                with open(out_filepath, 'wb') as f:
                    f.write(response.content)
                return True
        except Exception as e:
            print(f"    [!] Error downloading PDF: {e}")
            return False
    else:
        print("No pdf URL found, Skipping...", flush=True)

def download_audio(url: str, out_filepath: str):
    if url:
        print(f" -> Downloading Audio (FFmpeg): {url}", flush=True)
        command = ['ffmpeg', '-i', url, '-y', '-map', '0:a:0', '-vn', '-c:a', 'copy', out_filepath]
        
        try:
            # We use capture_output=True to keep the terminal clean
            subprocess.run(command, check=True, capture_output=True)
            return True
        except subprocess.CalledProcessError as e:
            print(f"    [!] FFmpeg error for sesion {url}: {e}", flush=True)
            return False
    else:
        print("No media URL found, Skipping", flush=True)
    

def main(args):
    leg_num = args.legislatura_num
    conn = None

    try:
        # Connect to DB
        conn = db.get_conn(db_path=args.db_path)
        cur = conn.cursor()

        # 1. Verify if the Legislatura exists
        cur.execute("SELECT id FROM legislatura WHERE num = ?", (leg_num,))
        result = cur.fetchone()
        if not result:
            print(f"Error: Legislatura number '{leg_num}' not found in database.", flush=True)
            return
        leg_id = result[0]

        # 2. Build filters based on arguments num=0 -> Plenos; num>0 -> Comisiones
        query_filters = []
        if args.download_pleno:
            query_filters.append("o.num = 0")
        if args.download_comision:
            query_filters.append("o.num > 0")
        
        if not query_filters:
            print("Notice: No download flags provided (--download_pleno or --download_comision). Exiting.", flush=True)
            return

        sql_filter = f"AND ({' OR '.join(query_filters)})"

        # 3. Fetch sessions and media URLs
        query = f"""
            SELECT s.id, s.num, s.pdf_url, o.num, m.m3u8_url, m.id
            FROM sesion s
            JOIN organo o ON s.organo_id = o.id
            JOIN media_url m ON s.id = m.sesion_id
            WHERE o.legislatura_id = ?
            AND m.m3u8_url IS NOT NULL
            AND (m.audio_filepath IS NULL OR s.pdf_filepath IS NULL)
            {sql_filter}
        """
        
        cur.execute(query, (leg_id,))
        sesion_list = cur.fetchall()

        total = len(sesion_list)
        print(f"Found {total} sessions to process for Legislatura {leg_num}...", flush=True)

        for i, (s_id, s_num, pdf_url, o_num, m3u8_url, m_id) in enumerate(sesion_list):
            print(f"\n[*] Session {i+1}/{total} [Legislatura: {leg_num}, Organo: {o_num}, Sesion: {s_num}, id: {m_id}]", flush=True)

            # Create directory structure
            o_type = 'pleno' if o_num==0 else 'comision'
            folder = f"data/legislatura_{leg_num}/{o_type}_{o_num}/sesion_{s_num}"
            os.makedirs(folder, exist_ok=True)
            
            filepath = f"{folder}/sesion_{leg_num}_{o_num}_{s_num}"
            pdf_filepath = f"{filepath}.pdf"
            audio_filepath = f"{filepath}_{m_id}.aac"

            # --- PDF ---
            # Only download if the file doesn't exist
            pdf_exists = os.path.exists(pdf_filepath)
            if not pdf_exists:
                if download_pdf(url=pdf_url, out_filepath=pdf_filepath):
                    cur.execute("UPDATE sesion SET pdf_filepath = ? WHERE id = ?", (pdf_filepath, s_id))
                    pdf_exists = True
                else:
                    # If PDF fails, not processable and media not ok
                    print(f"      [!] Critical: PDF download failed. Marking session as unprocessable.", flush=True)
                    cur.execute("UPDATE sesion SET is_processed = 0 WHERE id = ?", (s_id,))
                    cur.execute("UPDATE media_url SET is_ok = 0 WHERE id = ?", (m_id,))
                    conn.commit()
                    continue 

            # --- AUDIO ---
            if pdf_exists:
                # If PDF exists but we are here, could be that the audio is not correctly downloaded. Erase and repeat
                if os.path.exists(audio_filepath):
                    os.remove(audio_filepath)

                if download_audio(url=m3u8_url, out_filepath=audio_filepath):
                    cur.execute("UPDATE media_url SET audio_filepath = ?, is_ok = 1 WHERE id = ?", (audio_filepath, m_id))
                else:
                    cur.execute("UPDATE media_url SET is_ok = 0 WHERE id = ?", (m_id,))
            
            conn.commit()

        # Summary
        stats, detailed_stats = get_stats(conn)
        print_detailed_summary(stats, detailed_stats, title="TOTAL DATA")

    except KeyboardInterrupt:
        print("\n\n[!] Execution interrupted by user. Closing safely...", flush=True)
    except Exception as e:
        print(f"\n[!] Unexpected ERROR: {e}", flush=True)
    finally:
        if conn:
            conn.close()
            print("DB connection closed.", flush=True)
        print("Task finished.", flush=True)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Parliament Data Downloader", add_help=True)

    # Paths
    parser.add_argument("--db_path", type= str, required=True, help="(str): path to the SQLite DB")
    parser.add_argument("--output_dir", type=str, required=True, help="(str): The number of the Legislatura (e.g., 14)")

    # Inputs
    parser.add_argument("--legislatura_num", type=int, required=True, help="(int): the number of the Legislatura (e.g., 14)")

    # Flags
    parser.add_argument("--download_pleno", action="store_true", help="Enable download for 'Pleno' sessions")
    parser.add_argument("--download_comision", action="store_true", help="Enable download for 'Comision' sessions")
    
    args = parser.parse_args()
    main(args)