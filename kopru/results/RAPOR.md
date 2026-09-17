# Köprü deney raporu (otomatik üretildi)

Tohumlar: [0, 1, 2] · hızlı mod: False · toplam süre: 11.5 dk

## Ana tablo

Görev başarısı ölçütü: tatlı eğrisi hatası, implantsız lezyonlu beynin hatasının yarısından küçük olmalı (< 19.9 Hz). Acı-koruma skoru yalnızca görevi geçen koşullar için yorumlanır; görevi geçemeyen bir implant, beynin kendi kalan acı devresi yüzünden yüksek skor alabilir.

| Koşul | Tatlı eğrisi hatası (Hz) | Görev | Acı-koruma (0-1) | Yön (+ az, − fazla baskılama) | Tohum başına acı-koruma |
|---|---|---|---|---|---|
| Sağlam beyin, bağımsız tekrar (gürültü tabanı) | 1.3 ± 0.5 | referans | 0.94 ± 0.03 | +0.01 ± 0.02 | 0.92, 0.97, 0.91 |
| Lezyonlu, implantsız | 39.8 ± 0.4 | geçemedi | 0.49 ± 0.09 (yorumlanamaz) | -0.24 ± 0.03 | 0.60, 0.46, 0.39 |
| Erken okuma -> MN9'a yaz (kestirme) | 6.9 ± 1.6 | geçti | 0.36 ± 0.05 | +0.30 ± 0.01 | 0.41, 0.39, 0.29 |
| Erken okuma -> premotora yaz | 5.7 ± 1.0 | geçti | 0.18 ± 0.03 | +0.39 ± 0.01 | 0.22, 0.15, 0.18 |
| Geç okuma -> MN9'a yaz | 5.5 ± 0.6 | geçti | 0.55 ± 0.08 | -0.21 ± 0.03 | 0.65, 0.53, 0.47 |
| Geç okuma -> premotora yaz | 7.8 ± 0.4 | geçti | 0.62 ± 0.07 | -0.18 ± 0.03 | 0.71, 0.62, 0.53 |
| Sahte okuma -> MN9'a yaz (kontrol) | 26.0 ± 0.5 | geçemedi | 0.58 ± 0.03 (yorumlanamaz) | +0.15 ± 0.01 | 0.62, 0.55, 0.56 |

Acı-koruma: sağlam beyindeki acı baskılamasının ne kadarının korunduğu. 1 = sağlam beyinle aynı, 0 = tamamen kayıp. Hem eksik hem aşırı baskılama puanı düşürür. Yön: acılı koşullarda (MN9 oranı implant − MN9 oranı sağlam) ortalaması; + ise implant acıyı az duyuyor, − ise fazla duyuyor.

## Acı altında MN9 oranı (tohum ortalaması)

| Koşul | acı 0 Hz | acı 25 Hz | acı 50 Hz | acı 100 Hz | acı 200 Hz |
|---|---|---|---|---|---|
| Sağlam beyin | 1.00 | 0.90 | 0.79 | 0.39 | 0.02 |
| Sağlam beyin, bağımsız tekrar (gürültü tabanı) | 1.00 | 0.88 | 0.80 | 0.43 | 0.02 |
| Lezyonlu, implantsız | 1.00 | 0.80 | 0.30 | 0.02 | 0.02 |
| Erken okuma -> MN9'a yaz (kestirme) | 1.00 | 0.96 | 0.84 | 0.74 | 0.76 |
| Erken okuma -> premotora yaz | 1.00 | 1.02 | 0.92 | 0.86 | 0.86 |
| Geç okuma -> MN9'a yaz | 1.00 | 0.82 | 0.42 | 0.02 | 0.01 |
| Geç okuma -> premotora yaz | 1.00 | 0.83 | 0.53 | 0.03 | 0.01 |
| Sahte okuma -> MN9'a yaz (kontrol) | 1.00 | 0.93 | 0.70 | 0.54 | 0.55 |

## Tohum başına ayrıntı

### Tohum 0 · alt ağ 1366 nöron · 248 s

Lezyon: [720575940607272649, 720575940623211725] · premotor: 720575940619853515 (MN9'a 154 mV) · MN9: 720575940660219265

Erken okuma: 720575940622695448 (-, 1 adım, 143 Hz, acı-baskı 0.00), 720575940629888530 (-, 1 adım, 130 Hz, acı-baskı 0.00), 720575940627383685 (-, 1 adım, 128 Hz, acı-baskı -0.00), 720575940626191306 (-, 1 adım, 102 Hz, acı-baskı 0.02), 720575940638103349 (rattle, 1 adım, 101 Hz, acı-baskı -0.01)

Geç okuma: 720575940621586854 (-, 2 adım, 59 Hz, acı-baskı 0.96), 720575940633185567 (-, 2 adım, 59 Hz, acı-baskı 0.98), 720575940619877396 (-, 2 adım, 37 Hz, acı-baskı 0.98), 720575940631918649 (-, 2 adım, 36 Hz, acı-baskı 0.99), 720575940615671106 (-, 2 adım, 34 Hz, acı-baskı 0.98)

Sahte okuma: [720575940615271314, 720575940632644895, 720575940611207922, 720575940617244027, 720575940615311010]

| Tasarım | Kazanç | Eşik (Hz) | Tatlı hatası | Acı-koruma | Yön | Kaba ızgara sınırında mı |
|---|---|---|---|---|---|---|
| Erken okuma -> MN9'a yaz (kestirme) | 1 | 40 | 7.3 | 0.41 | +0.30 | hayır |
| Erken okuma -> premotora yaz | 1.875 | 60 | 6.9 | 0.22 | +0.40 | hayır |
| Geç okuma -> MN9'a yaz | 2.625 | 10 | 6.4 | 0.65 | -0.18 | hayır |
| Geç okuma -> premotora yaz | 5.25 | 10 | 7.4 | 0.71 | -0.15 | hayır |
| Sahte okuma -> MN9'a yaz (kontrol) | 1 | -30 | 25.7 | 0.62 | +0.14 | hayır |

Tam beyin doğrulaması (aynı tohum, 4 koşul):

- erken_mn9: en büyük MN9 farkı 0.00 Hz
- erken_premotor: en büyük MN9 farkı 0.00 Hz
- gec_mn9: en büyük MN9 farkı 0.00 Hz
- gec_premotor: en büyük MN9 farkı 0.00 Hz
- sahte_mn9: en büyük MN9 farkı 0.00 Hz

### Tohum 1 · alt ağ 1356 nöron · 220 s

Lezyon: [720575940607272649, 720575940623211725] · premotor: 720575940619853515 (MN9'a 154 mV) · MN9: 720575940660219265

Erken okuma: 720575940622695448 (-, 1 adım, 142 Hz, acı-baskı -0.00), 720575940629888530 (-, 1 adım, 128 Hz, acı-baskı -0.01), 720575940627383685 (-, 1 adım, 127 Hz, acı-baskı -0.01), 720575940626191306 (-, 1 adım, 102 Hz, acı-baskı -0.00), 720575940638103349 (rattle, 1 adım, 102 Hz, acı-baskı 0.00)

Geç okuma: 720575940621586854 (-, 2 adım, 64 Hz, acı-baskı 0.94), 720575940633185567 (-, 2 adım, 64 Hz, acı-baskı 0.97), 720575940631918649 (-, 2 adım, 40 Hz, acı-baskı 1.00), 720575940619877396 (-, 2 adım, 38 Hz, acı-baskı 1.00), 720575940615671106 (-, 2 adım, 34 Hz, acı-baskı 1.00)

Sahte okuma: [720575940641655949, 720575940636963806, 720575940630342364, 720575940624566535, 720575940642142683]

| Tasarım | Kazanç | Eşik (Hz) | Tatlı hatası | Acı-koruma | Yön | Kaba ızgara sınırında mı |
|---|---|---|---|---|---|---|
| Erken okuma -> MN9'a yaz (kestirme) | 1 | 40 | 4.7 | 0.39 | +0.29 | hayır |
| Erken okuma -> premotora yaz | 2.625 | 70 | 4.5 | 0.15 | +0.40 | hayır |
| Geç okuma -> MN9'a yaz | 3.75 | 20 | 4.9 | 0.53 | -0.22 | hayır |
| Geç okuma -> premotora yaz | 6 | 10 | 7.5 | 0.62 | -0.18 | hayır |
| Sahte okuma -> MN9'a yaz (kontrol) | 1 | -40 | 26.7 | 0.55 | +0.15 | hayır |

### Tohum 2 · alt ağ 1337 nöron · 220 s

Lezyon: [720575940607272649, 720575940623211725] · premotor: 720575940619853515 (MN9'a 154 mV) · MN9: 720575940660219265

Erken okuma: 720575940622695448 (-, 1 adım, 144 Hz, acı-baskı 0.02), 720575940629888530 (-, 1 adım, 130 Hz, acı-baskı 0.01), 720575940627383685 (-, 1 adım, 129 Hz, acı-baskı 0.01), 720575940626191306 (-, 1 adım, 103 Hz, acı-baskı 0.02), 720575940638103349 (rattle, 1 adım, 103 Hz, acı-baskı 0.01)

Geç okuma: 720575940621586854 (-, 2 adım, 61 Hz, acı-baskı 0.94), 720575940633185567 (-, 2 adım, 60 Hz, acı-baskı 0.95), 720575940631918649 (-, 2 adım, 38 Hz, acı-baskı 1.00), 720575940619877396 (-, 2 adım, 36 Hz, acı-baskı 1.00), 720575940615671106 (-, 2 adım, 35 Hz, acı-baskı 1.00)

Sahte okuma: [720575940632503608, 720575940632295751, 720575940628623612, 720575940623499400, 720575940606607234]

| Tasarım | Kazanç | Eşik (Hz) | Tatlı hatası | Acı-koruma | Yön | Kaba ızgara sınırında mı |
|---|---|---|---|---|---|---|
| Erken okuma -> MN9'a yaz (kestirme) | 0.812 | 20 | 8.7 | 0.29 | +0.32 | hayır |
| Erken okuma -> premotora yaz | 1.5 | 50 | 5.7 | 0.18 | +0.37 | hayır |
| Geç okuma -> MN9'a yaz | 3.75 | 20 | 5.2 | 0.47 | -0.24 | hayır |
| Geç okuma -> premotora yaz | 12 | 20 | 8.4 | 0.53 | -0.21 | evet |
| Sahte okuma -> MN9'a yaz (kontrol) | 1.875 | -20 | 25.6 | 0.56 | +0.17 | hayır |
