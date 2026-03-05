from tabulate import tabulate

def get_stats(conn):
    cur = conn.cursor()

    query = """
        SELECT
            (SELECT COUNT(*) FROM legislatura) as legislaturas,
            COUNT(DISTINCT CASE WHEN o.num = 0 THEN o.id END) as plenos,
            COUNT(DISTINCT CASE WHEN o.num > 0 THEN o.id END) as comisiones,

            -- TOTAL
            COUNT(CASE WHEN o.num = 0 THEN s.id END) as sesiones_pleno,
            COUNT(CASE WHEN o.num > 0 THEN s.id END) as sesiones_comision,

            -- AVAILABLE (is_processed IS NULL OR is_processed = 1)
            COUNT(CASE WHEN o.num = 0 AND (s.is_processed IS NULL OR s.is_processed = 1) THEN s.id END) as sesiones_pleno_available,
            COUNT(CASE WHEN o.num > 0 AND (s.is_processed IS NULL OR s.is_processed = 1) THEN s.id END) as sesiones_comision_available,

            -- DOWNLOADED (is_ok = 1)
            SUM(CASE WHEN mu.is_ok = 1 AND o.num = 0 THEN 1 ELSE 0 END) as media_pleno_downloaded,
            SUM(CASE WHEN mu.is_ok = 1 AND o.num > 0 THEN 1 ELSE 0 END) as media_comision_downloaded,

            -- PROCESSED (is_processed = 1)
            COUNT(CASE WHEN o.num = 0 AND s.is_processed = 1 THEN s.id END) as sesiones_pleno_processed,
            COUNT(CASE WHEN o.num > 0 AND s.is_processed = 1 THEN s.id END) as sesiones_comision_processed

        FROM organo o
        LEFT JOIN sesion s ON o.id = s.organo_id
        LEFT JOIN media_url mu ON mu.sesion_id = s.id
    """
    cur.execute(query)
    columns = [column[0] for column in cur.description]
    row = cur.fetchone()
    stats = dict(zip(columns, row)) if row else {col: 0 for col in columns}

    detailed_query = """
        SELECT
            l.num as legislatura,
            o.num as organo,
            o.name as nombre,
            COUNT(s.id) as sesiones,
            COUNT(CASE WHEN s.is_processed IS NULL OR s.is_processed = 1 THEN s.id END) as sesiones_available,
            SUM(CASE WHEN mu.is_ok = 1 THEN 1 ELSE 0 END) as media_downloaded,
            COUNT(CASE WHEN s.is_processed = 1 THEN s.id END) as sesiones_processed
        FROM legislatura l
        JOIN organo o ON l.id = o.legislatura_id
        LEFT JOIN sesion s ON o.id = s.organo_id
        LEFT JOIN media_url mu ON mu.sesion_id = s.id
        GROUP BY l.num, o.num
        ORDER BY l.num DESC, o.num ASC
    """
    
    cur.execute(detailed_query)
    columns = [column[0] for column in cur.description]
    detailed_stats = [dict(zip(columns, row)) for row in cur.fetchall()]

    return stats, detailed_stats

def calculate_stats_diff(fin_stats, fin_detailed_stats, ini_stats, ini_detailed_stats):
    # Global stats
    new_stats = {k: fin_stats[k] - ini_stats[k] for k in ini_stats.keys()}

    # Map for fast search on detailed_stats
    ini_map = { (d['legislatura'], d['organo']): (d['sesiones'], d['sesiones_available'], d['sesiones_processed']) for d in ini_detailed_stats }
    
    new_detailed_stats = []    
    for row in fin_detailed_stats:
        legislatura = row['legislatura']
        organo = row['organo']
        key = (legislatura, organo)
        ini_ses, ini_ses_avail, ini_ses_proc = ini_map.get(key, (0, 0, 0))
        
        # Calculate diff
        new_ses = row['sesiones'] - ini_ses
        new_ses_avail = row['sesiones_available'] - ini_ses_avail
        new_ses_proc = row['sesiones_processed'] - ini_ses_proc
        
        # Only add if there are new sesiones
        if new_ses > 0:
            new_detailed_stats.append({
                'legislatura': legislatura,
                'organo': organo,
                'nombre': row['nombre'],
                'sesiones': new_ses,
                'sesiones_available': new_ses_avail,
                'sesiones_processed': new_ses_proc
            })

    return new_stats, new_detailed_stats

def _print_leg_table(leg_num, leg_items):
    # Add total summary and then print
    t_total = sum([items[2] for items in leg_items])
    t_avail = sum([items[3] for items in leg_items])
    t_procs = sum([items[4] for items in leg_items])

    leg_items.append(["","- TOTAL", t_total, t_avail, t_procs])
    table_detail = tabulate(
        leg_items,
        headers=["ID", "NAME", "TOTAL", "AVAILABLE", "DOWNLOADED", "PROCESSED"],
        tablefmt="github",
        numalign="right"
    )
    m_div = len(table_detail.split("\n")[0])
    print(f"\n{'-'*m_div}")
    title = f"LEGISLATURA: {leg_num}"
    print(f"{title:^{m_div}}") # Centrado relativo
    print(f"{'-'*m_div}")
    print(table_detail)

def print_detailed_summary(stats, detailed_stats, title="PARLIAMENT DATA"):
    global_data = [
        ["Plenos", stats['sesiones_pleno'], stats['sesiones_pleno_available'], stats['media_pleno_downloaded'], stats['sesiones_pleno_processed']],
        ["Comisiones", stats['sesiones_comision'], stats['sesiones_comision_available'], stats['media_comision_downloaded'], stats['sesiones_comision_processed']]
    ]

    global_table = tabulate(
        global_data, 
        headers=["ORGANO", "TOTAL", "AVAILABLE", "DOWNLOADED", "PROCESSED"],
        tablefmt="github",
        numalign="right"
    )

    n_div = len(global_table.split("\n")[0])

    print("\n" + "="*n_div)
    print(f"{title:^{n_div}}")
    print("="*n_div)
    print(global_table)

    # Detailed stats
    current_leg = None
    leg_items = []
    for item in detailed_stats:
        if current_leg is None:
            current_leg = item['legislatura']
        
        if  current_leg != item['legislatura']:
            _print_leg_table(current_leg, leg_items)

            # Reset for the next
            current_leg = item['legislatura']
            leg_items = []

        # Format name and add
        short_name = (item['nombre'][:35] + '...') if len(item['nombre']) > 35 else item['nombre']
        
        leg_items.append([
            item['organo'],
            short_name, 
            item['sesiones'], 
            item['sesiones_available'], 
            item['media_downloaded'], 
            item['sesiones_processed']
        ])

    # Print the last one
    if leg_items:
        _print_leg_table(current_leg, leg_items)

    print("\n" + "="*n_div)