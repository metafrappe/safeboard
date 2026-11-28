# Engel yaşam döngüsü ve Kural 7 için sahte veri

Bu klasör AJA-2321 işinde yazıldı. Kaynak AJA-2145 tasarım belgesinin 5. bölümüdür.

Bu veri sahtedir. Veri gerçek kayıttan alınmadı. Veride kişisel bilgi ve gizli bilgi yoktur.

## Dosyalar

| Dosya | İçinde ne var? |
| --- | --- |
| `cases.json` | On iki durumun girdisi. |
| `expected.json` | On iki durumun beklenen sonucu. |
| `rte_thresholds.json` | Sahte RTE kaydı. Kural 7 eşiği ve dönemi buradadır. |

Testi `backend/tests/test_blocker_lifecycle_fixtures.py` dosyası koşar.

## On iki durum

| No | Durum | Tasarım bölümü |
| --- | --- | --- |
| 1 | Engel beş aşamadan sırayla geçer. | 5.1 |
| 2 | "Sahiplendi" ve "Eskale edildi" birlikte olur. | 5.1 |
| 3 | Bekleyen işi olmayan engel yalnız sinyalin yokluğuyla doğrulanır. | 5.1 |
| 4 | Çözülmüş ama doğrulanmamış engelin sinyali döner. | 5.2 |
| 5 | Doğrulanmış engelin sinyali döner. Yeni dönem açılır. | 5.2 |
| 6 | Kural kök neden kodu verir. Sonra insan kodu değiştirir. | 5.3 |
| 7 | Kodu `unknown.unclassified` olan engel doğrulanır. | 5.3 |
| 8 | Aynı `blocker_key` dönem içinde eşikten çok açılır. | 5.4 |
| 9 | Aynı kök neden kodu farklı anahtarlarda eşikten çok görülür. | 5.4 |
| 10 | Açık aday varken engel bir kez daha açılır. | 5.4 |
| 11 | Eşiğin altında kalan engel aday açmaz. | 5.4 |
| 12 | "Kaizen adayı yap" düğmesiyle elle aday açılır. | 5.4 |

## Girdi nasıl okunur?

Her durumun dört girdisi vardır.

- `audit_events` alanı defter satırlarını taşır. Zarf AJA-2140 tasarımının 1.2 bölümündeki zarftır.
- `collect_runs` alanı toplama kayıtlarını taşır. Her kayıt bir okumadır.
- `context.blockers` alanı engelin kök işini, sahibini ve bekleyen işlerini verir.
- `context.kaizen_items` alanı testten önce açık olan Kaizen adaylarını verir.

`context.blockers` bilgisini gerçekte engel tablosu hesaplar. Bu veri o hesabı denemez. Bu yüzden bilgi hazır verilir.

Defter satırında özet alanları yoktur. `prev_hash` ve `row_hash` değerini defter yazan kod hesaplar.

## Beklenen sonuç nasıl okunur?

Her durumun dört sonucu vardır.

- `episodes` alanı dönemleri verir. Her dönemde aşama listesi vardır. Liste `stage_history` alanıdır.
- `episode_count` alanı dönem sayısını verir.
- `ledger_events` alanı kodun deftere yazacağı yeni olayları verir.
- `kaizen_candidates` alanı testten sonra açık olan Kaizen adaylarını verir.

1. durumdan 7. duruma kadar `ledger_events` listesi boştur. Çünkü aşama değişimi deftere yazılmaz. Aşama kaynak olaylardan çıkar.

## Eşik ve dönem

Eşik ve dönem `rte_thresholds.json` dosyasındadır. Bu sayılar sahtedir. Gerçek eşiği Team SAFe RTE yazar.

Sahte sayılar gerçek sayılardan bilerek farklıdır. Böylece koda sabit sayı yazan test kırılır.

Kodunuz eşiği bu kayıttan okumalıdır. Sayıyı koda yazmayın.

## Tasarımın açık yazmadığı noktalar

Tasarım aşağıdaki noktaları açık yazmıyor. Bu veri her nokta için bir okuma seçti. Okuma yanlışsa veriyi Team B PO ile düzeltin.

1. **Dönem kimliği.** `blocker_id` değeri burada anahtar, `@` işareti ve açılış anıdır. Bu biçim sahtedir. Testiniz kimliği parçalamasın.
2. **Olay kimliği.** Girdideki `event_uid` değerleri yalnız tekildir. Testiniz bu değeri parçalamasın. Beklenen yeni olaylarda `event_uid` yoktur.
3. **Aşama adı.** `stage` değeri tasarımdaki Türkçe addır. Örneğin "Açıldı" yazar.
4. **Doğrulama kanıtı.** "Doğrulandı" aşaması bir toplama kaydına dayanır. Bu kayıt `collect_runs` alanındadır. Kayıt defter satırı değildir.
5. **Bekleyen işin ilerlemesi.** Bekleyen işin `issue.status_changed` olayı ilerleme sayılır.
6. **Geri dönüş işareti.** Aynı dönemde "Açıldı" aşamasına dönüş `returned` alanıyla işaretlenir.
7. **`recurrence_count` değeri.** Değer aynı anahtarın aynı haftadaki açılış sayısıdır. Sayım o dönemin açılışına kadar yapılır.
8. **`payload` anahtarları.** `from`, `to`, `status`, `action_type` ve `root_cause_code` adlarını bu veri seçti.
9. **Kural adı.** Kural 7 adayının `rule_key` değeri `rule7` olur. Bu ad RTE kaydındaki anahtardır.
10. **Toplam bekleyen iş.** Veride toplam ile tekil sayı aynı çıkar. Böylece iki okuma da aynı sonucu verir.
11. **"Son aşama".** 2. durumda önce sahiplenme, sonra eskalasyon olur. Ters sıra bu veride yoktur.
12. **Elle açılan aday.** 12. durumda girdi `action.requested` olayıdır. Beklenen yeni olay `kaizen.candidate_created` olayıdır.

## Testi koşmak

Depo kökünde şu komutu çalıştırın:

```bash
python3 -I -m unittest discover -s backend/tests -t backend -v
```

Test şunları denetler:

- On iki durumun girdisi ve beklenen sonucu vardır.
- Defterde aşama değişimi olayı yoktur.
- Veride gerçek kayıt izi yoktur.
- Beklenen dönemler kaynak olaylardan çıkar.
- Tablo silinip yeniden kurulunca aşamalar aynı kalır.
- Kural 7 sonuçları sahte RTE kaydıyla tutarlıdır.

`backend/tests/blocker_lifecycle_reference.py` dosyası yalnız test içindir. Bu dosya ürün kodu değildir.
