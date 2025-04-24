from flask import Flask, render_template, request, send_file
import os
import requests
import json
import csv
from datetime import datetime
import matplotlib.pyplot as plt
from collections import Counter
from wordcloud import WordCloud
from fpdf import FPDF

app = Flask(__name__)

# Create folders
os.makedirs("static/charts", exist_ok=True)
os.makedirs("static/data", exist_ok=True)
os.makedirs("report", exist_ok=True)

@app.route("/", methods=["GET", "POST"])
def index():
    products = []
    error = None
    brand_chart = origin_chart = nutriscore_chart = wordcloud_img = ""
    today = datetime.now().strftime("%Y-%m-%d")
    time_now = datetime.now().strftime("%H:%M:%S")

    selected_brand = "Carrefour"
    selected_origin = "France"

    if request.method == "POST":
        selected_brand = request.form.get("brand", "Carrefour").strip()
        selected_origin = request.form.get("origin", "France").strip()

        url = (
            "https://world.openfoodfacts.org/cgi/search.pl"
            f"?action=process&tagtype_0=brands&tag_contains_0=contains&tag_0={selected_brand}"
            f"&tagtype_1=origins&tag_contains_1=contains&tag_1={selected_origin}&json=true&page_size=200"
        )
        try:
            response = requests.get(url)
            data = response.json()
        except Exception as e:
            error = f"API Error: {e}"
            return render_template("index.html", products=[], brand=selected_brand, origin=selected_origin,
                                   error=error, brand_chart="", origin_chart="", nutriscore_chart="", wordcloud="",
                                   date=today, time=time_now)

        # Save JSON
        with open("static/data/products.json", "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)

        brand_counter = []
        origin_counter = []
        nutriscore_counter = []
        ingredients_all = []

        for product in data.get("products", []):
            code = product.get("code", "N/A")
            name = product.get("product_name", "N/A")
            ingredients = product.get("ingredients_text", "N/A")
            if name != "N/A":
                products.append([code, name, ingredients])
                brand_counter.append(product.get("brands", "unknown"))
                origin_counter.append(product.get("origins", "unknown"))
                nutriscore_counter.append(product.get("nutriscore_grade", "unknown"))
                ingredients_all.append(ingredients)

        if products:
            with open("static/data/products.csv", "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(["Barcode", "Product Name", "Ingredients"])
                writer.writerows(products)

            def plot_counter(data, title, filename):
                counter = Counter(data)
                labels, values = zip(*counter.items()) if counter else ([], [])
                plt.figure(figsize=(6, 4))
                plt.bar(labels, values, color="skyblue")
                plt.title(title)
                plt.xticks(rotation=45)
                plt.tight_layout()
                path = f"static/charts/{filename}"
                plt.savefig(path)
                plt.close()
                return path

            brand_chart = plot_counter(brand_counter, "Brand Frequency", "brand_chart.png")
            origin_chart = plot_counter(origin_counter, "Origin Frequency", "origin_chart.png")
            nutriscore_chart = plot_counter(nutriscore_counter, "Nutri-score Distribution", "nutriscore_chart.png")

            wordcloud = WordCloud(width=800, height=400, background_color='white').generate(" ".join(ingredients_all))
            wordcloud_path = "static/charts/wordcloud.png"
            wordcloud.to_file(wordcloud_path)
            wordcloud_img = wordcloud_path

            # PDF Report
            pdf = FPDF()
            pdf.add_page()
            pdf.set_font("Arial", "B", 16)
            pdf.cell(200, 10, "OpenFoodFacts Report", ln=True, align="C")
            pdf.set_font("Arial", "", 12)
            pdf.cell(200, 10, f"Date: {today}    Time: {time_now}", ln=True)
            pdf.cell(200, 10, f"Brand: {selected_brand}    Origin: {selected_origin}", ln=True)
            pdf.ln(10)
            for title, img in [("Nutri-score", nutriscore_chart), ("Brand", brand_chart), ("Origin", origin_chart), ("Ingredients", wordcloud_img)]:
                pdf.cell(200, 10, title, ln=True)
                pdf.image(img, w=180)
            pdf.output("report/summary_report.pdf")
        else:
            error = "No products found for the selected brand and country."

    return render_template("index.html", products=products, brand=selected_brand, origin=selected_origin,
                           brand_chart=brand_chart, origin_chart=origin_chart,
                           nutriscore_chart=nutriscore_chart, wordcloud=wordcloud_img,
                           error=error, date=today, time=time_now)

@app.route("/download/<filetype>")
def download(filetype):
    paths = {
        "json": "static/data/products.json",
        "csv": "static/data/products.csv",
        "pdf": "report/summary_report.pdf"
    }
    path = paths.get(filetype)
    if path and os.path.exists(path):
        return send_file(path, as_attachment=True)
    return "File not found", 404

if __name__ == "__main__":
    app.run(debug=True, port=5000)
