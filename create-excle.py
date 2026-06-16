import pandas as pd

# Data dari lo yang udah dirapikan ke dalam list
list_hp = ["Number_Your_Phone"]
list_puk = ["Number_Your_PUK"]

list_nik = ['Number_Your_NIK']

list_kk = ['Number_Your_KK']
df = pd.DataFrame({
    'No_HP': list_hp,
    'PUK': list_puk,
    'NIK': list_nik,
    'KK': list_kk
})

df = df.astype(str)

# Simpan menimpa file lama
with pd.ExcelWriter('dagangan.xlsx', engine='openpyxl') as writer:
    df.to_excel(writer, index=False)

print("✅ Sukses Total! File 'dagangan.xlsx' sekarang datanya sudah 100% lurus dan benar.")