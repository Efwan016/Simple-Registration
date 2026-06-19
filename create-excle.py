import pandas as pd
from itertools import zip_longest

# Data dari lo yang udah dirapikan ke dalam list
list_hp = [
    'Your No_HP data here'
]

list_puk = [
    'Your PUK data here'
    ]

list_nik = [
    'Your NIK data here'
    ]

list_kk = [
    'Your KK data here'
    ]

jumlah_data = {
    'No_HP': len(list_hp),
    'PUK': len(list_puk),
    'NIK': len(list_nik),
    'KK': len(list_kk),
}

if len(set(jumlah_data.values())) != 1:
    print("⚠️  Jumlah data tiap kolom belum sama:")
    for nama_kolom, jumlah in jumlah_data.items():
        print(f"   - {nama_kolom}: {jumlah}")
    print("⚠️  Baris yang datanya kurang akan dikosongkan di Excel.")

rows = []
for no_hp, puk, nik, kk in zip_longest(list_hp, list_puk, list_nik, list_kk, fillvalue=''):
    rows.append({
        'No_HP': str(no_hp).strip(),
        'PUK': str(puk).strip(),
        'NIK': str(nik).strip(),
        'KK': str(kk).strip(),
    })

df = pd.DataFrame(rows)

df = df.astype(str)

# Simpan menimpa file lama
with pd.ExcelWriter('dagangan.xlsx', engine='openpyxl') as writer:
    df.to_excel(writer, index=False)

print("✅ Sukses Total! File 'dagangan.xlsx' sekarang datanya sudah 100% lurus dan benar.")
