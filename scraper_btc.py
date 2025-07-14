from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import pandas as pd
import firebase_admin
from firebase_admin import credentials, db
import json
import os

# Configurações do Selenium
options = webdriver.ChromeOptions()
options.add_argument('--headless')
options.add_argument('--no-sandbox')
options.add_argument('--disable-dev-shm-usage')

try:
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    driver.set_page_load_timeout(30)

    url_btc_historico = "https://coinmarketcap.com/currencies/bitcoin/historical-data/"
    driver.get(url_btc_historico)

    table_historico = WebDriverWait(driver, 20).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, ".cmc-table"))
    )
    rows_historico = table_historico.find_elements(By.TAG_NAME, "tr")

    data_historico = []
    for row in rows_historico[1:]:
        cols = row.find_elements(By.TAG_NAME, "td")
        cols = [col.text.strip() for col in cols]
        if cols:
            data_historico.append(cols)

    df_historico = pd.DataFrame(data_historico, columns=["Date", "Open", "High", "Low", "Close", "Volume", "Market Cap"])
    
    # Converter colunas numéricas
    for col in ["Open", "High", "Low", "Close", "Volume", "Market Cap"]:
        df_historico[col] = df_historico[col].replace(r'[\$,]', '', regex=True).astype(float)
    
    print(f"Dados históricos extraídos: {len(df_historico)} linhas.")

except Exception as e:
    print(f"Erro ao extrair dados: {str(e)}")
    df_historico = pd.DataFrame()

finally:
    driver.quit()

if df_historico.empty:
    print("Erro: Nenhum dado foi extraído.")
    exit(1)

# Firebase
firebase_json = os.environ.get("FIREBASE_CREDENTIALS")
if not firebase_json:
    print("Erro: FIREBASE_CREDENTIALS não definida.")
    exit(1)
try:
    cred_dict = json.loads(firebase_json)
    cred = credentials.Certificate(cred_dict)
    firebase_admin.initialize_app(cred, {
        "databaseURL": "https://coinapp-e7fe4-default-rtdb.firebaseio.com/"
    })
    print("Firebase inicializado com sucesso.")
except Exception as e:
    print(f"Erro ao inicializar o Firebase: {e}")
    exit(1)

historico_ref = db.reference("historico_btc")
timestamp = time.strftime('%Y%m%d')
data_to_save = {f"{timestamp}{i}": row.to_dict() for i, row in df_historico.iterrows()}
try:
    historico_ref.set(data_to_save)
    print("Dados gravados com sucesso no Firebase.")
except Exception as e:
    print(f"Erro ao gravar dados: {str(e)}")