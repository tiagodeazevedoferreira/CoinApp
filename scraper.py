from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import firebase_admin
from firebase_admin import credentials, firestore
import pandas as pd
import time
import os
from dotenv import load_dotenv

load_dotenv()
cred_path = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')

cred = credentials.Certificate(cred_path)
firebase_admin.initialize_app(cred)
db = firestore.client()

options = webdriver.ChromeOptions()
options.add_argument('--headless')
options.add_argument('--no-sandbox')
options.add_argument('--disable-dev-shm-usage')
driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

try:
    url = "https://coinmarketcap.com/"
    driver.get(url)
    time.sleep(5)

    table = WebDriverWait(driver, 20).until(
        EC.presence_of_element_located((By.CLASS_NAME, 'cmc-table'))
    )
    rows = table.find_elements(By.TAG_NAME, 'tr')

    data = []
    for row in rows:
        cols = row.find_elements(By.TAG_NAME, 'td')
        if len(cols) >= 7:
            nome = cols[2].text.split('\n')[0]
            simbolo = cols[2].text.split('\n')[1]
            preco = cols[3].text
            variacao_24h = cols[4].text
            variacao_7d = cols[5].text
            market_cap = cols[6].text
            volume_24h = cols[7].text if len(cols) > 7 else ""
            data.append({
                'nome': nome,
                'simbolo': simbolo,
                'preco': preco,
                'variacao_24h': variacao_24h,
                'variacao_7d': variacao_7d,
                'market_cap': market_cap,
                'volume_24h': volume_24h,
                'timestamp': firestore.SERVER_TIMESTAMP
            })

    for moeda in data:
        doc_ref = db.collection('moedas').document(moeda['simbolo'])
        doc_ref.set(moeda)
        print(f"Salvo: {moeda['simbolo']} - {moeda['nome']}")

except Exception as e:
    print(f"Erro ao executar scraper: {e}")

finally:
    driver.quit()
