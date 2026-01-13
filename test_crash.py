from strategies.soros_gale_session import SorosGaleSession
import pandas as pd

# Test 1: Init Session
session = SorosGaleSession(100, 87, 5, 3)

# Test 2: Win
session.registrar_win()
print(session.historico[-1])

# Test 3: Loss
session.registrar_loss()
print(session.historico[-1])

# Test 4: DataFrame Construction (to check column names)
df = pd.DataFrame(session.historico)
print("Columns:", df.columns)

try:
    subset = df[['Nível Soros', 'Gale', 'Entrada', 'Resultado', 'Saldo Sessão']]
    print("Subset OK")
except KeyError as e:
    print(f"KeyError: {e}")
