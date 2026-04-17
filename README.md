# Parliamentary Scraping Project

A robust data scraping system for downloading metadata, PDFs, and audio streams from parliamentary plenary and commission sessions. This project organizes all content into a structured SQLite database with automated logging and statistics.

## Features

* **Plenary & Commission Metadata Scraping**: Extract XML data for plenary and commission sessions
* **Media Download**: PDFs and audio streams (via FFmpeg) automatically downloaded and organized
* **Database Integration**: SQLite database storing legislaturas, órganos, sesiones, and media URLs
* **Statistics & Reporting**: Built-in analytics for total and detailed session coverage
* **Automated Execution**: Shell scripts for running metadata scraping and media downloads
* **Logging**: Detailed logs for each execution, tracking progress and errors

## Project Structure

```
.
├── data/                   # Downloaded PDF and media files
├── db/
│   ├── __init__.py
│   ├── db.py               # Database operations
│   └── database.db         # SQLite database file
├── logs/
│   ├── download_data/
│   └── scrap_metadata/
├── run_download_data.sh     # Run PDF and media downloads for a given Legislature
├── run_scrap_metadata.sh    # Run web and XML metadata scraping
├── run_task.sh              # Universal task runner
├── requirements.txt         # Python dependencies
└── src/
    ├── __init__.py
    ├── download_data.py
    ├── scrap_metadata.py
    └── stats_utils.py
```

## Installation

### Prerequisites

* Python 3.8+
* FFmpeg (for audio downloads)
* SQLite3

### Setup

1. Clone the repository:

```bash
git clone https://github.com/hitz-zentroa/scrap_parliament.git
cd scrap_parliament
```

2. Install Python dependencies:

```bash
pip install -r requirements.txt
```

3. Install FFmpeg (if not already installed):

```bash
# Ubuntu/Debian
sudo apt-get install ffmpeg

# macOS
brew install ffmpeg

# Or download from https://ffmpeg.org/download.html
```

## Usage

### Metadata Scraping

Scrape all legislative metadata (plenary and commission XMLs) and populate the database:

```bash
./run_scrap_metadata.sh
```

**Arguments** are set in the script or can be passed manually, including:

* `--db_path` → Path to the SQLite DB
* `--output_dir` → Directory to store XML files
* `--pleno_url` → URL for plenary XMLs
* `--base_comisiones_url` → Base URL for commissions XMLs
* `--save_xml` → Optional: save XML files locally
* `--only_stats` → Optional: print stats without scraping

### Media Download

Download PDFs and audio streams for a specific legislatura:

```bash
./run_download_data.sh
```

**Flags**:

* `--legislatura_num` → The number of the legislatura to download
* `--download_pleno` → Include plenary sessions
* `--download_comision` → Include commission sessions

Media is stored under:

```
data/legislatura_<num>/<pleno|comision>_<organo>/sesion_<num>/
```

### Direct Python Execution

You can also run modules directly:

```bash
cd src
python scrap_metadata.py --db_path db/database.db --pleno_url <URL> --base_comisiones_url <URL>
python download_data.py --db_path db/database.db --output_dir data --legislatura_num 14 --download_pleno --download_comision
```

## Database

The SQLite DB tracks all sessions and media:

### Tables

* **legislatura**: Parliament legislature information
* **organo**: Plenary (num=0) or commission (num>0)
* **sesion**: Individual session details (dates, PDFs)
* **media_url**: Audio stream URLs, download status, local file paths

## Logging

All task executions generate logs under:

```
logs/scrap_metadata/YYYYMMDD_HHMMSS.log
logs/download_data/YYYYMMDD_HHMMSS.log
```

Logs include:

* Start and end timestamps
* Progress of scraping or download
* Success/failure of media retrieval
* Elapsed time

## Dependencies

Key packages:

* **requests**: HTTP requests
* **beautifulsoup4**: HTML parsing
* **tqdm**: Progress bars
* **tabulate**: Pretty printing statistics
* **ffmpeg**: Audio extraction
* **sqlite3**: Database operations (built-in)

See `requirements.txt` for full versions.

## Development

Focus areas for enhancement:

* Optimize DB schema and indexes
* Add retry and error handling for failed media
* Improve scraping speed and concurrency
* Extend support for new parliament sources

## Copyright 2026 HiTZ

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.

## Acknowledgements
This work has been partially supported by the Basque Government (IKER-GAITU project), the Spanish Ministry for Digital Transformation and of Civil Service, and the EU-funded NextGenerationEU Recovery, Transformation and Resilience Plan (ILENIA project, 2022/TL-22/00215335 & ALIA).

## Support

For issues or questions, contact: **[asierherranzv@gmail.com](mailto:asierherranzv@gmail.com)**
