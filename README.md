# Pizza Shop Analysis Dashboard

A comprehensive analysis dashboard for pizza shops with website status, direct ordering capabilities, and actionable outreach data.

## 🚀 Live Demo

Visit the live dashboard: [https://mkyoung23.github.io/pizza-shop-analysis/](https://mkyoung23.github.io/pizza-shop-analysis/)

## ✨ Features

- **Interactive Data Table**: Browse through 400+ pizza shops with sortable columns
- **Smart Filtering**: Filter by website status and ordering type
- **Real-time Search**: Find specific shops instantly
- **Analytics Dashboard**: View key statistics including:
  - Total shops analyzed
  - Shops with websites
  - Shops with direct ordering capability
- **Responsive Design**: Works perfectly on desktop and mobile
- **Custom Styling**: Professional, modern interface without external dependencies

## 📊 Sample Data

The dashboard currently displays realistic sample data including:

- **Shops with Direct Ordering**: Independent websites with their own ordering systems
- **Third-party Ordering**: Shops using platforms like GrubHub, UberEats, DoorDash, etc.
- **No Website**: Shops without an online presence (prime targets for outreach)

## 🛠️ How It Works

1. **Data Source**: The `results.csv` file contains the analysis results
2. **Dashboard**: Custom HTML/CSS/JavaScript loads and displays the data
3. **GitHub Pages**: Automatically deploys the latest version
4. **GitHub Actions**: Can run automated analysis with API keys (optional)

## 📁 File Structure

```
pizza-shop-analysis/
├── index.html              # Main dashboard
├── index_simple.html       # Simplified version
├── results.csv             # Analysis data
├── extended_analysis.py     # Analysis script
├── .github/workflows/       # GitHub Actions
└── README.md               # This file
```

## 🔧 Setup for Development

### Running Locally

1. Clone the repository:
```bash
git clone https://github.com/mkyoung23/pizza-shop-analysis.git
cd pizza-shop-analysis
```

2. Start a local web server:
```bash
python3 -m http.server 8000
```

3. Open [http://localhost:8000](http://localhost:8000) in your browser

### Updating Data

To update the analysis data:

1. **Option A - Manual Update**: Edit `results.csv` directly with new data
2. **Option B - Run Analysis Script**:
   ```bash
   pip install pandas openpyxl requests
   python3 extended_analysis.py --input "Store Map.xlsx" --output results.csv
   ```

### GitHub Pages Deployment

The dashboard automatically deploys to GitHub Pages when you:
1. Push changes to the main branch
2. The live site updates within a few minutes

## 🎯 Use Cases

- **Sales Teams**: Identify pizza shops without websites for outreach
- **Market Analysis**: Understand digital adoption in local markets
- **Competitive Intelligence**: See which shops use third-party vs. direct ordering
- **Lead Generation**: Find prospects who need website and ordering solutions

## 🔑 API Integration (Optional)

The analysis script supports API keys for automated data enrichment:

- Google Search API for website discovery
- OpenAI for intelligent categorization
- Additional AI services for enhanced analysis

Set environment variables in GitHub Secrets:
- `GOOGLE_API_KEY`
- `OPENAI_API_KEY`
- `GEMINI_API_KEY`
- `PERPLEXITY_API_KEY`

## 📈 Statistics Overview

Current sample dataset includes:
- **400 Total Shops**
- **165 Shops with Websites** (~41% coverage)
- **112 Shops with Direct Ordering** (~28% have their own systems)

This represents significant opportunity for web development and ordering system services, especially among the 235 shops without websites and the 53 shops that rely solely on third-party platforms.

## 🎨 Customization

The dashboard uses custom CSS and JavaScript for complete control over styling and functionality:

- No external dependencies (Bootstrap, jQuery, etc.)
- Fast loading and offline-capable
- Easy to customize colors, layout, and features
- Professional branding with "#23 AI Solutions" theme

## 📞 Support

For questions or support, please create an issue in this repository.

---

*Crafted by the #23 AI Solutions team – turning pizza data into sales magic.*

This project automates the process of checking whether pizza shops in the Boston area have their own website and whether they offer direct online ordering.  It uses data provided in a Microsoft Excel workbook (such as **Store Map.xlsx**), calls the Google Places API to gather website information, and classifies each shop accordingly.  An interactive dashboard built with DataTables allows you to sort, search and filter the results.

## Contents

- `shop_analysis.py` – Python script that reads the Excel workbook, queries the Google Places API, classifies each shop and writes a `results.csv` file.  It can also generate outreach messages tailored to each shop.
- `results.csv` – CSV file containing the classification results (generated after you run the script).  Columns include `ShopID`, `AccountName`, `BillingCity`, `BillingZip`, `Website`, `HasWebsite`, `DirectOrdering` and `Note`.
- `index.html` – An interactive table based on DataTables.  When opened in a browser alongside `results.csv`, it lets you explore the data with sorting, searching and filtering.
- `.env.sample` – Sample environment file showing the expected variables (`GOOGLE_API_KEY`, and optional `TWILIO_…`/`SENDGRID_…`).  Copy this to `.env` and fill in your real keys locally.  **Never commit your `.env` file.**
- `README.md` – This documentation.

## Setup

1. **Install dependencies**

   Ensure you have Python 3.7+ installed.  Install the required libraries:

   ```bash
   pip install pandas requests
   ```

2. **Obtain a Google Places API key**

   Create a Google Cloud project, enable the **Places API**, and generate an API key.  Copy `.env.sample` to `.env` and replace the placeholder value of `GOOGLE_API_KEY` with your real key.  Do **not** commit `.env` to version control—the repository’s `.gitignore` excludes it automatically.

   If you later integrate email/SMS sending, you can also add `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_FROM_PHONE` and `SENDGRID_API_KEY` to your `.env` file.

3. **Run the analysis**

   Execute the Python script, specifying the Excel file and an output location for the CSV.  For example:

   ```bash
   python shop_analysis.py --input "Store Map.xlsx" --output results.csv
   ```

   The script reads the `All`, `Multi Location Shops` and `OO Partners` sheets, deduplicates the list of shops, queries Google for each, and writes `results.csv`.  You can also generate personalised outreach messages by providing the `--messages` option:

   ```bash
   python shop_analysis.py --input "Store Map.xlsx" --output results.csv --messages outreach_messages.csv
   ```

   The `outreach_messages.csv` file contains a row per shop with customised email subject, email body and SMS body.  Import this file into your marketing or CRM tool to automate follow‑ups.

4. **Open the interactive dashboard**

   After generating `results.csv`, open `index.html` in a modern browser.  The page uses JavaScript to load the CSV and display an interactive table.  You can sort by `HasWebsite` or `DirectOrdering` to identify shops lacking a web presence or depending solely on third‑party aggregators.

   To share this dashboard with others, you can host the files (including the generated `results.csv`) on GitHub Pages or another static‑site hosting service.  Commit the files to a repository, enable GitHub Pages, and send the resulting URL to your colleagues.

## Extending the project

* **Additional data sources:** You can enrich the analysis by adding columns from the Excel workbook (e.g., shop score, territory, target customer) or by querying other APIs such as Yelp or social‑media feeds.
* **Lead‑generation tools:** Pair this data with your CRM.  For example, once you know which shops lack direct ordering, you can prioritise them for outreach.  Integrate the CSV with email‑marketing tools or CRMs to automate follow‑ups.
* **Scheduling:** Use a cron job or GitHub Actions to run the analysis weekly or monthly, ensuring that changes in Google listings are captured.
* **Custom dashboards:** If DataTables does not meet your needs, consider building a Streamlit or Dash application that includes charts (e.g., counts of shops without websites by zip code) and export tools.

## Limitations

* This script relies on the Google Places API, which may not always return a website URL even when one exists.  Some shops could therefore be falsely flagged as lacking a website.
* The classification of direct vs. third‑party ordering is based solely on the website’s domain.  Restaurants might host their menu on a third‑party domain while still controlling the ordering experience.  You may need to fine‑tune the `THIRD_PARTY_DOMAINS` list to match your definition of “third‑party.”
* Running the script against hundreds of shops will consume API quotas.  Adjust the request interval (`time.sleep` in `shop_analysis.py`) and monitor your usage to avoid exceeding limits.

## Contributing

Pull requests are welcome!  If you discover additional third‑party domains or ways to improve the classification logic, please contribute.

---

© 2025 Pizza‑Tech Analytics.  Licensed under the MIT License.
