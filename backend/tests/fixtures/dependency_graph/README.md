# Bağımlılık grafiği için sahte veri

Bu klasörde bağımlılık grafiğinin sahte verisi ve beklenen sonuçları durur.
Geliştiriciler testlerini bu veriye göre yazar.

Veri uydurmadır. Hiçbir kayıt gerçek bir işten alınmadı.
İş numaraları `ORN-` ile başlar. Depo adları `ornek-org` ile başlar.
Veride kişi adı, adres ve gizli bilgi yoktur.

## Dosyalar

| Dosya | İçeriği |
| --- | --- |
| `main.json` | 1, 2, 3, 4, 5, 6, 7, 8 ve 10 numaralı durumlar |
| `tie_length.json` | 9. durum: uzun zincir kazanır |
| `tie_active.json` | 9. durum: daha çok aktif işi açan zincir kazanır |
| `tie_teams.json` | 9. durum: daha çok takımı açan zincir kazanır |
| `tie_oldest.json` | 9. durum: beklemesi daha önce başlayan zincir kazanır |

Her dosyada iki bölüm vardır.

- `input` bölümü sahte Paperclip ve sahte GitHub kaydıdır.
- `expected` bölümü backend'in bu kayıttan üretmesi gereken sonuçtur.

Dosyayı `tests/dependency_fixture.py` içindeki `load_scenario` fonksiyonu okur.

## On durum nerede?

| No | Durum | `main.json` içindeki yeri |
| --- | --- | --- |
| 1 | Beş düğüm türü | `expected.nodes`: iş, takım, repo, PR ve dış engel |
| 2 | Team B işi Team A işini bekler | `ORN-101` işi `ORN-102` işini bekler. `cross_team` değeri `true` olur. |
| 3 | Aynı takımın iki işi | `ORN-102` işi `ORN-103` işini bekler. `cross_team` değeri `false` olur. |
| 4 | Üç iş bağı tek takım bağı olur | Team B üç işle Team A'yı bekler. Takım bağında `count` değeri 3 yazar. |
| 5 | `parentId` bağı | `ORN-121` işinin üst işi `ORN-123` işidir. Bu iki iş arasında bağ yoktur. |
| 6 | Yorumdaki bağ | `ORN-131` işinin yorumunda "ORN-132 bekliyor" yazar. Bağ `inferred` olur. |
| 7 | Kırık bağın sekiz türü | `expected.broken_cases` listesi |
| 8 | Döngü | `ORN-151`, `ORN-152` ve `ORN-153` birbirini bekler. |
| 9 | Eşitlik kuralları | Dört `tie_*.json` dosyası |
| 10 | Üç kapsam | `expected.critical_path`: bütün şirket, `PI-1`, `PI-2` ve Team SAFe |

## Kırık bağın sekiz türü

Türler tanım belgesinin 7.3 bölümündeki sıradadır.

| No | Tür | `broken_kind` kodu | Bağ |
| --- | --- | --- | --- |
| 1 | Beklenen iş iptal edildi | `dep.broken_cancelled` | `ORN-141` işi `ORN-142` işini bekler |
| 2 | Bayat engel bağı | `dep.stale_done_blocker` | `ORN-143` işi `ORN-144` işini bekler |
| 3 | Taban PR birleşmeden kapandı | `dep.broken_closed_base` | PR 10, PR 9'u bekler |
| 4 | Döngü | `dep.broken_cycle` | `ORN-151`, `ORN-152`, `ORN-153` |
| 5 | Kök iş ertelenmiş | `proc.backlog_root` | `ORN-161` işi `ORN-162` işini bekler |
| 6 | Bağlı PR eski depoda | `dep.broken_legacy_repo` | `ORN-171` işinin PR'ı eski depodadır |
| 7 | Bağ yalnız yorumda | `dep.unrecorded` | `ORN-131` işi `ORN-132` işini bekler |
| 8 | Hedef bulunamadı | `dep.broken_missing_target` | `ORN-181` işi `ORN-999` işini bekler |

## Kritik yol

Kritik yol süreyle hesaplanmaz. Beklenen sonuçlarda süre tahmini yoktur.

Eşitlik sırası şöyledir:

1. En uzun zincir kazanır.
2. Eşitlikte kökü çözülünce daha çok aktif işi açan zincir kazanır.
3. Yine eşitlikte daha çok takımı açan zincir kazanır.
4. Yine eşitlikte beklemesi daha önce başlayan zincir kazanır.

Her `tie_*.json` dosyasında iki zincir vardır. Dosyanın kuralı kazananı belirler.
Sıradaki kurallar tek başına öbür zinciri seçerdi. Böylece yanlış sıra testte yakalanır.

`decided_by` alanı kararı veren kuralı yazar.
Değerler `length`, `unlocked_active_issues`, `unlocked_teams` ve `oldest_wait` olur.

## Tasarımın açık bıraktığı yerler

Tasarım belgesi bazı ayrıntıları yazmıyor. Bu veri o ayrıntılarda şu varsayımları kullanır.
Bir varsayım yanlışsa Team SAFe System Architect karar verir. Sonra bu veri düzeltilir.

1. İkinci kırık türün kodu `dep.stale_done_blocker` olur. Kod olay defteri sözlüğünden alındı.
2. Beşinci kırık türün kodu `proc.backlog_root` olur. Sahipsiz kök bu veride yoktur.
3. Kırık bağın `state` değeri `broken` olur. Yorumdaki bağ da `broken` yazar.
4. İş engelli değilse ve beklediği iş bittiyse bağ `resolved` olur. Örnek `ORN-132` bağıdır.
5. Zincir uzunluğu açık bağ sayısıdır. Alanın adı `edge_count` olur.
6. Kritik yol yalnız açık ve kayıtlı iş bağlarından hesaplanır.
7. Zincirdeki bütün işler kapsamın içindeyse zincir o kapsama girer.
8. Açılan aktif işler, köke açık bağlarla bağlı aktif işlerdir. Kök sayılmaz. `backlog` işi sayılmaz.
9. Zincirin yaşı, zincirdeki en eski `blockedAt` değeridir.
10. Takım bağı ve repo bağı `explicit` yazar. Çünkü kaynak bağlar kayıtta yazılıdır.
11. Takımı olmayan düğümde `cross_team` değeri `false` olur. Örnek PR ve dış engel düğümüdür.
12. Bulunamayan iş `missing` işaretli bir düğüm olur.
13. `rule_version` alanı bu veride yoktur. Değeri kodu yazan iş belirler.

Veri bu varsayımlara karşı sağlam kuruldu. Örneğin en uzun zincirde yalnız iş bağı vardır.
Bu yüzden zincir uzunluğu düğümle de sayılsa kazanan değişmez.

## Test

Şu komut veriyi denetler. Komutu `backend` klasöründe çalıştırın.

```
python3 -I -m unittest discover -s tests -t . -v
```

Test, beklenen sonuçları kurallardan yeniden hesaplar. Sonuç tutmazsa test kırmızı olur.
