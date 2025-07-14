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
import time

# Configurações do Selenium
options = webdriver.ChromeOptions()
options.add_argument('--headless=new')  # Novo modo headless para evitar detecção
options.add_argument('--no-sandbox')
options.add_argument('--disable-dev-shm-usage')
options.add_argument('--disable-blink-features=AutomationControlled')  # Evita detecção anti-bot
options.add_argument('user-agent=Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36')

try:
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    driver.set_page_load_timeout(30)

    url_btc_historico = "https://coinmarketcap.com/currencies/bitcoin/historical-data/"
    driver.get(url_btc_historico)

    # Função para encontrar a tabela
    def find_table():
        try:
            # Tentar no contexto principal
            table = WebDriverWait(driver, 30).until(
                EC.visibility_of_element_located((By.CSS_SELECTOR, "table[class*='table']"))
            )
            print("Tabela encontrada no contexto principal.")
            return table
        except:
            print("Tabela não encontrada no contexto principal. Verificando iframes...")
        
        # Tentar em iframes
        try:
            iframes = driver.find_elements(By.TAG_NAME, "iframe")
            print(f"Encontrados {len(iframes)} iframes.")
            for index, iframe in enumerate(iframes):
                driver.switch_to.default_content()
                driver.switch_to.frame(iframe)
                print(f"Alternado para iframe {index}.")
                try:
                    table = WebDriverWait(driver, 10).until(
                        EC.visibility_of_element_located((By.CSS_SELECTOR, "table[class*='table']"))
                    )
                    print(f"Tabela encontrada no iframe {index}.")
                    return table
                except:
                    print(f"Tabela não encontrada no iframe {index}.")
                    driver.switch_to.default_content()
        except:
            print("Nenhum iframe encontrado ou acessível.")
            driver.switch_to.default_content()
        
        raise Exception("Tabela não encontrada em nenhum contexto.")

    # Rolar a página para garantir carregamento completo
    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
    time.sleep(2)  # Espera breve para renderização

    # Encontrar a tabela
    table_historico = find_table()

    # Reencontrar as linhas dinamicamente
    def get_rows():
        return WebDriverWait(driver, 30).until(
            EC.visibility_of_all_elements_located((By.CSS_SELECTOR, "table[class*='table'] tr"))
        )

    data_historico = []
    retries = 3
    for attempt in range(retries):
        try:
            rows_historico = get_rows()
            print(f"Encontradas {len(rows_historico)} linhas na tabela.")
            for row in rows_historico[1:]:  # Ignorar cabeçalho
                cols = row.find_elements(By.TAG_NAME, "td")
                cols = [col.text.strip() for col in cols if col.text.strip()]
                if cols and len(cols) >= 7:  # Garante que a linha tem todas as colunas esperadas
                    data_historico.append(cols[:7])  # Limita às 7 colunas esperadas
            break
        except Exception as e:
            print(f"Tentativa {attempt + 1} falhou: {str(e)}")
            if attempt < retries - 1:
                time.sleep(2)
                driver.switch_to.default_content()
                table_historico = find_table()  # Reencontrar tabela
            else:
                raise Exception("Falha após todas as tentativas.")

    if not data_historico:
        raise Exception("Nenhuma linha válida extraída da tabela.")

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