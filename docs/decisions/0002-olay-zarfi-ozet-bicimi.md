# 0002: Olay zarfının özet biçimi, izin listesi ve takma ad

Bu karar 28 Kasım 2026 Cumartesi günü AJA-2661 işinde verildi.

Bu not AJA-2140 tasarım belgesinin 1.2, 1.6 ve 1.7 bölümlerini ayrıntılandırır. Not tasarımı değiştirmez. Not ile tasarım çelişirse tasarım geçerlidir.

Bu notta kod yoktur. Örneklerdeki bütün kimlikler sahtedir.

## Kısa sözlük

- **Defter** `audit_event` tablosudur.
- **Zarf** her defter satırının taşıdığı alanlardır.
- **Bağ** `event_object` tablosundaki bir satırdır.
- **Özet** bir metnin SHA-256 değeridir.
- **Özet metni** özeti hesaplanan JSON metnidir.

## Ortak biçim kuralları

Bu kurallar özet metninin her yerinde geçerlidir.

1. Özet metni tek bir JSON nesnesidir.
2. Anahtarlar her derinlikte sıraya dizilir. Sıra Unicode kod noktasına göredir. Büyük harf küçük harften önce gelir. Türkçe alfabe sırası kullanılmaz.
3. Anahtar adları yalnız ASCII karakterlerinden oluşur. ASCII, Türkçe harf içermeyen temel karakter kümesidir. Bu kural `payload` içindeki her derinlikte geçerlidir. Böylece her programlama dili anahtarları aynı sıraya dizer.
4. Metinde boşluk ve satır sonu olmaz. Ayırıcılar yalnız `,` ve `:` işaretidir.
5. Metin UTF-8 olur. Değerlerdeki Türkçe harfler olduğu gibi yazılır. Harfler `\u` biçimine çevrilmez. Harflerin Unicode biçimi de değiştirilmez.
6. Metnin içinde yalnız üç şey kaçış işaretiyle yazılır. Bunlar çift tırnak, ters eğik çizgi ve denetim karakterleridir. Bu kural RFC 8785 belgesindeki metin kuralıyla aynıdır.
7. Boş alan `null` yazılır. Boş alan metinden çıkarılmaz.
8. Sayılar yalnız tam sayıdır. Ondalıklı sayı yazılmaz.
9. Tam sayı en az -9007199254740991, en çok 9007199254740991 olur. JavaScript daha büyük sayıyı bozar.
10. Metinde eşi olmayan vekil karakter bulunmaz. Vekil karakter, UTF-16 metnindeki yarım harf parçasıdır. Bu parça UTF-8'e çevrilemez.
11. Zarf alanlarının türü şöyledir:
    - `id` ve `schema_version` tam sayıdır.
    - `payload` bir nesnedir. `payload` hiçbir zaman `null` olmaz.
    - `prev_hash` metindir. `prev_hash` hiçbir zaman `null` olmaz.
    - Diğer zarf alanları metin ya da `null` olur.
12. Zaman metni tabloda nasıl duruyorsa özet metnine öyle girer. Zaman biçimi AJA-2047 sözleşmesindeki biçimdir. Örnek: `2026-11-28T09:14:02.000Z`.
13. Özet, özet metninin UTF-8 baytlarından hesaplanır. Özet 64 karakterlik küçük harfli onaltılık metin olarak yazılır.

Python'daki `json` modülü üç ayarla bu biçimi verir. `sort_keys` açık olur. Ayırıcılar `,` ve `:` olur. `ensure_ascii` kapalı olur.

### Kurala uymayan değer

`audit.record()` şu dört durumda olayı reddeder. Deftere satır yazılmaz.

1. Bir değer ondalıklı sayıdır. Bu kural her derinlikte geçerlidir.
2. Bir tam sayı 9. kuraldaki aralığın dışındadır.
3. Bir metinde eşi olmayan vekil karakter vardır.
4. Bir anahtar adında ASCII dışı karakter vardır.

**Örnek.** `payload` içinde `{"exitCode":1.5}` gelir. `1.5` ondalıklı sayıdır. `audit.record()` olayı reddeder.

## Karar 1: Özet metnine giren zarf alanları

`row_hash` dışındaki bütün zarf alanları özet metnine girer. `id`, `recorded_at` ve `prev_hash` alanları da girer.

2. sürümde özet metninde 29 anahtar vardır. 28 anahtar zarf alanıdır. 1 anahtar bağ listesidir.

2. sürümün zarf alanları şunlardır:

`account_certainty`, `account_ref`, `action`, `actor_id`, `actor_kind`, `actor_role`, `causation_id`, `corrects_event_uid`, `correlation_id`, `event_uid`, `id`, `issue_id`, `model`, `observed_after`, `occurred_at`, `outcome`, `payload`, `pr_ref`, `prev_hash`, `recorded_at`, `requirement_id`, `run_id`, `schema_version`, `source`, `source_code`, `source_ref`, `team`, `time_basis`.

`id` alanı özete girdiği için `audit.record()` bu değeri satırı yazmadan önce belirler. `id` değeri son satırın `id` değerinin bir fazlasıdır. Defter boşsa `id` değeri 1 olur.

`audit.record()` son satırı okur ve yeni satırı aynı veritabanı işleminde yazar. İşlem yazma kilidini okumadan önce alır. Böylece iki yazıcı aynı `id` değerini alamaz.

`prev_hash` alanına bir önceki satırın `row_hash` değeri yazılır. Bir önceki satır, `id` değeri bir küçük olan satırdır.

**Örnek.** Son satırın `id` değeri 1 ise yeni satırın `id` değeri 2 olur. Yeni satırın `prev_hash` değeri 1. satırın `row_hash` değeridir. Tam örnek bu notun sonundadır.

## Karar 2: Bağların özet metnine girişi

Bağlar özet metnine `objects` anahtarıyla girer. `objects` bir listedir.

Listenin her öğesi bir bağdır. Her bağın dört alanı girer: `link_basis`, `object_id`, `object_kind` ve `recorded_at`. `event_id` alanı girmez. Çünkü bu değer satırın `id` alanıyla aynıdır.

Liste önce `object_kind`, sonra `object_id` değerine göre dizilir. Sıra yine Unicode kod noktasına göredir.

`object_kind` ve `object_id` değerleri yalnız ASCII karakterlerinden oluşur. Değerde ASCII dışı karakter varsa `audit.record()` olayı reddeder. Böylece her programlama dili bağları aynı sıraya dizer.

Satırın hiç bağı yoksa `objects` değeri boş liste olur. Boş liste `[]` diye yazılır.

Bir olayda aynı `object_kind` ve `object_id` çifti yalnız bir kez bulunur.

Bir bağ her zaman tek bir defter satırına aittir. Bağ o satırla aynı veritabanı işleminde yazılır. Bu yüzden bağın `recorded_at` değeri satırın `recorded_at` değeriyle aynıdır.

**Örnek.** Bir satırın iki bağı var. Birinci bağ `issue` türünde ve `is-0050` kimliğindedir. İkinci bağ `agent` türünde ve `ajan-0011` kimliğindedir. Özet metninde önce `agent` bağı yazılır. Çünkü `agent` sırada `issue` kelimesinden önce gelir.

## Karar 3: `payload` alanının özet metnine girişi

`payload` özet metnine iç içe bir JSON nesnesi olarak girer. `payload` tırnak içinde tek bir metin olarak girmez.

`payload` içindeki anahtarlar da her derinlikte sıraya dizilir. Listelerin sırası değişmez.

`payload` hiçbir zaman `null` olmaz. Ayrıntı yoksa `payload` boş nesne olur. Boş nesne `{}` diye yazılır.

**Örnek.** Çağıran şu ayrıntıyı verir:

```json
{"to":"İncelemede","from":{"b":1,"a":null}}
```

Özet metnine şu parça girer:

```json
{"from":{"a":null,"b":1},"to":"İncelemede"}
```

## Karar 4: 1. sürümün alan listesi

1. sürüm AJA-2081 belgesinin 3. sorusundaki tablodur. O tabloda 13 alan vardır.

1. sürümde özet metninde 13 anahtar vardır. 12 anahtar o tablodan gelir. `row_hash` girmez. 13. anahtar `schema_version` alanıdır ve değeri 1 olur.

1. sürümün alanları şunlardır:

`action`, `actor_id`, `actor_kind`, `id`, `issue_id`, `occurred_at`, `payload`, `prev_hash`, `recorded_at`, `schema_version`, `source`, `source_ref`, `team`.

1. sürümde `objects` anahtarı yoktur. Çünkü 1. sürümde bağ tablosu yoktu.

Eski satırın `schema_version` alanında 1 değeri durur. Doğrulayıcı alan listesini bu değere göre seçer.

Doğrulayıcı 1. sürüm satırında iki şeye daha bakar:

1. 2. sürüm 16 zarf alanı ekler. `schema_version` dışındaki 15 alan boş olmalıdır. Biri doluysa doğrulama başarısız olur.
2. Satırın hiç bağı olmamalıdır. Bir bağ varsa doğrulama başarısız olur.

Yeni satırlar her zaman 2. sürümle yazılır. 1. sürüm yalnız eski satırları doğrulamak içindir.

**Örnek.** 1. sürümle yazılmış bir satırın özet metni şudur:

```json
{"action":"issue.status_changed","actor_id":"ajan-0007","actor_kind":"agent","id":1,"issue_id":"is-0042","occurred_at":"2026-11-27T08:00:00.000Z","payload":{"from":"todo","to":"in_progress"},"prev_hash":"0000000000000000000000000000000000000000000000000000000000000000","recorded_at":"2026-11-27T08:00:05.000Z","schema_version":1,"source":"paperclip","source_ref":"etkinlik-0001","team":"team_b"}
```

Bu metnin SHA-256 değeri şudur:

```text
0871334d18db5bb33511878c15ae81572f36bb6846aa8616fa3eb13b85a22dca
```

## Karar 5: İlk satırın `prev_hash` değeri

Defterin ilk satırında `prev_hash` değeri 64 tane sıfırdır.

Bu değer `null` değildir. Böylece `prev_hash` alanı hiçbir satırda boş kalmaz. Doğrulayıcı boş bir `prev_hash` görürse doğrulama başarısız olur.

64 sıfır yalnız `id` değeri en küçük olan satırda bulunabilir. Başka bir satırda bulunursa doğrulama başarısız olur.

**Örnek.** 4. karardaki örnek satır defterin ilk satırıdır. O satırın `prev_hash` değeri şudur:

```text
0000000000000000000000000000000000000000000000000000000000000000
```

## Karar 6: `payload` izin listeleri

İzin listesi bir olay türünün `payload` içinde taşıyabileceği anahtarların listesidir.

### Genel kurallar

1. İzin listeleri tek yerde durur. Bu yer `audit` modülüdür.
2. İzin listesi `payload` alanının en üst düzey anahtarlarına bakar.
3. Bir anahtarın değeri düz değer olur. Düz değer metin, tam sayı, `true`, `false` ya da `null` değeridir.
4. İç içe nesne ve liste yalnız izin listesi açıkça söylerse yazılır.
5. Bir olay türü hiç ayrıntı taşımıyorsa o türe boş bir izin listesi yazılır.

### Kurala uymayan `payload`

Üç ayrı durum vardır.

1. **Anahtar listede yoktur.** `audit.record()` bu anahtarı atar ve satırı yine yazar. Özet, kalan `payload` ile hesaplanır. Atılan anahtarın değeri hiçbir yere yazılmaz. Yalnız anahtarın adı uyarı olarak günlüğe yazılabilir.
2. **Anahtar listededir ama değeri izinsiz bir nesne ya da listedir.** `audit.record()` olayı reddeder. Deftere satır yazılmaz. Çünkü beklenen bir bilgi yanlış biçimde gelmiştir.
3. **Değer ortak biçim kurallarına uymaz.** `audit.record()` olayı reddeder. Örneğin değer ondalıklı sayıdır. Bu kural izinli iç içe değerin her derinliğinde geçerlidir.

Sıra şöyledir. `audit.record()` önce listede olmayan anahtarları atar. Sonra kalan değerleri denetler. Atılan bir anahtarın değeri olayı reddettirmez.

**Örnek 1.** `run.finished` olayı `status` ve `logText` anahtarlarıyla gelir. `logText` listede yoktur. `audit.record()` `logText` anahtarını atar. Deftere yalnız `{"status":"failed"}` yazılır.

**Örnek 2.** `run.finished` olayı `{"status":{"kod":"failed"}}` ile gelir. `status` listededir ama değeri bir nesnedir. `audit.record()` olayı reddeder.

### Bu özellikteki listeler

| Olay türü | İzinli anahtarlar |
| --- | --- |
| `event.corrected` | `fields` |
| `event.linked` | `target_event_uid` |

Diğer olay türlerinin listesini o olay türünü getiren özellik ekler. Özellik listeyi kendi PR'ında `audit` modülüne yazar. Özellik aynı PR'da listenin testini de yazar.

Tasarım `run.finished` listesini 1.7 bölümünde verir. Tasarım token sayılarının anahtar adlarını vermez. Bu adları koşu olaylarını getiren özellik yazar.

### `event.corrected` kuralları

1. Yanlış satırın kimliği `payload` içine yazılmaz. Bu kimlik zarftaki `corrects_event_uid` alanına yazılır.
2. Düzeltme satırının `event_uid` değeri `safeboard:audit_event:<id>:corrected` biçimindedir. `<id>` düzeltme satırının kendi `id` değeridir. Bu biçim tasarımın 1.2 bölümündeki SAFeBoard tarifine uyar.
3. Aynı satır birden çok kez düzeltilebilir. Her düzeltme satırının `id` değeri ayrıdır. Bu yüzden her düzeltmenin `event_uid` değeri de ayrıdır.
4. Aynı alan iki kez düzeltildiyse `id` değeri büyük olan düzeltme geçerlidir.
5. `fields` bir nesnedir. Nesnenin her anahtarı bir zarf alanının adıdır. Değer o alanın doğru değeridir.
6. Doğru değer metin ya da `null` olur. Doğru değer boşsa `null` yazılır. Tek istisna `payload` anahtarıdır.
7. Yedi zarf alanı düzeltilemez. Bu alanlar `id`, `event_uid`, `schema_version`, `recorded_at`, `prev_hash`, `row_hash` ve `corrects_event_uid` alanlarıdır.
8. `fields` içinde `payload` anahtarı olabilir. Bu değer bir nesnedir. Bu değer yanlış satırın bütün `payload` alanının yerine geçer.
9. `fields` içindeki `payload` da izin listesinden geçer. Kullanılan liste yanlış satırın olay türünün listesidir. `fields` içinde `action` da varsa yeni olay türünün listesi kullanılır.
10. Gizlilik kuralları `fields` için de geçerlidir. Örneğin `actor_id` düzeltilirken gerçek ad yazılmaz, takma ad yazılır.

`audit.record()` şu altı durumda düzeltme olayını reddeder. Deftere satır yazılmaz.

1. `payload` içinde `fields` anahtarı yoktur.
2. `fields` boş bir nesnedir.
3. `fields` içinde düzeltilemeyen yedi alandan biri vardır. Örneğin `row_hash` vardır.
4. `fields` içinde zarf alanı olmayan bir ad vardır. Örneğin `renk` vardır.
5. `corrects_event_uid` boştur ya da defterde bu kimlikle bir satır yoktur.
6. `corrects_event_uid` bir `event.corrected` satırını gösterir. Düzeltme satırı düzeltilmez. Düzeltme yanlışsa asıl satıra yeni bir düzeltme yazılır.

**Örnek.** Bir `run.finished` satırı sonucu `failed` diye yazmıştı. Doğru sonuç `cancelled` idi. Düzeltme satırı defterin 3. satırıdır. Satır şöyle olur:

- `action` değeri `event.corrected` olur.
- `event_uid` değeri `safeboard:audit_event:3:corrected` olur.
- `corrects_event_uid` değeri `paperclip:run:kosu-0009:finished` olur.
- `payload` değeri şudur:

```json
{"fields":{"outcome":"cancelled","payload":{"errorCode":"user_cancelled","status":"cancelled"},"source_code":"user_cancelled"}}
```

Bu örnekte eski `payload` içindeki `status` değeri de yanlıştı. Bu yüzden `fields` yeni `payload` değerini de taşır.

### `event.linked` kuralları

1. `target_event_uid` bağın eklendiği eski olayın `event_uid` değeridir.
2. `event.linked` satırının `event_uid` değeri `safeboard:audit_event:<id>:linked` biçimindedir. `<id>` bu satırın kendi `id` değeridir.
3. Yeni bağ `event_object` tablosuna yazılır. Bağın `event_id` değeri `event.linked` satırının `id` değeridir.
4. Yeni bağ eski satırın `id` değeriyle yazılmaz. Böylece eski satırın özeti değişmez.
5. Yeni bağ `event.linked` satırının `objects` listesine girer. Böylece yeni bağ da bir özetle korunur.
6. `event.linked` satırında `issue_id`, `run_id`, `pr_ref` ve `requirement_id` alanları boş kalır.
7. Bir olayın bütün bağları iki yerden okunur. Birinci yer olayın kendi bağlarıdır. İkinci yer o olayı gösteren `event.linked` satırlarının bağlarıdır.

`audit.record()` şu üç durumda bağ olayını reddeder. Deftere satır yazılmaz.

1. `payload` içinde `target_event_uid` anahtarı yoktur ya da değeri boştur.
2. Defterde `target_event_uid` kimliğiyle bir satır yoktur.
3. `event.linked` satırının hiç bağı yoktur.

**Örnek.** Koşu olayının `ornek/depo#57` numaralı PR'a da bağlı olduğu sonradan bulundu. Yeni satır defterin 4. satırıdır. Satır şöyle olur:

- `action` değeri `event.linked` olur.
- `event_uid` değeri `safeboard:audit_event:4:linked` olur.
- `payload` değeri şudur:

```json
{"target_event_uid":"paperclip:run:kosu-0009:finished"}
```

- Satırın tek bağı vardır. Bağın `object_kind` değeri `pr` olur. `object_id` değeri `ornek/depo#57` olur. `link_basis` değeri `inferred` olur.

## Karar 7: İzin listesi olmayan olay türü

İzin listesi olmayan bir olay türü gelirse `audit.record()` olayı reddeder. Deftere satır yazılmaz. Bağ da yazılmaz.

`audit.record()` çağırana bir hata verir. Hatada olay türünün adı bulunur. Hatada `payload` içeriği bulunmaz.

Olayı toplayıcı gönderdiyse toplayıcı `collect_run` kaydına bir uyarı yazar. Toplayıcı diğer olayları yazmaya devam eder.

Bu kuralın nedeni şudur. Listesi olmayan olay türü ya yazım hatasıdır ya da listesi unutulmuş bir türdür. İki durumda da neyin gizli olduğu bilinmez.

**Örnek.** Toplayıcı `run.finishd` adıyla bir olay gönderir. Bu adın izin listesi yoktur. `audit.record()` olayı reddeder. Toplayıcı `collect_run` kaydına şu uyarıyı yazar: "İzin listesi olmayan olay türü: `run.finishd`".

## Karar 8: Takma adın biçimi

Takma ad `kisi-` ön eki ile bir tam sayıdan oluşur. Örnek: `kisi-3`.

1. Sayı 1'den başlar. Her yeni kişi bir sonraki sayıyı alır.
2. Sayının başına sıfır yazılmaz. `kisi-03` yanlıştır.
3. Takma ad, kişinin deftere yazılan ilk işleminde verilir. Panoya yalnız bakan kişiye takma ad verilmez. Deftere ilk işlemi yazılan kişi `kisi-1` olur.
4. Backend Tailscale adını karşılaştırmadan önce düzeltir. Baştaki ve sondaki boşluklar silinir. Harfler küçük harfe çevrilir.
5. Küçük harfe çevirme bilgisayarın dil ayarına bağlı olmaz. `I` harfi her zaman `i` olur. `I` harfi `ı` olmaz.
6. Aynı kişi her zaman aynı takma adı alır.
7. Bir sayı ikinci kez kullanılmaz.
8. Eşleşme silinince tablodaki gerçek ad silinir. Takma adın satırı kalır. Böylece o sayı başkasına verilmez.
9. Eşleşmesi silinen kişi panoya yeniden gelirse yeni bir sayı alır.
10. Takma ad yalnız `actor_kind` değeri `board_user` olan satırlarda kullanılır.
11. Localhost aşamasında Tailscale adı yoktur. O zaman `actor_id` değeri `local` olur. Bu kural AJA-2081 belgesindendir.
12. Gerçek Tailscale adı `payload` alanına da yazılmaz.

**Örnek.** Panoyu önce birinci kişi, sonra ikinci kişi kullanır. Birinci kişi `kisi-1`, ikinci kişi `kisi-2` olur. Sonra `kisi-2` eşleşmesi silinir. Panoya üçüncü bir kişi gelir. Üçüncü kişi `kisi-3` olur. `kisi-2` adı kimseye verilmez.

## Tam örnek: bir satır, iki bağ, özet metni ve özet

Bu satır defterin 2. satırıdır. 1. satır 4. karardaki örnek satırdır.

### Satırın zarf alanları

| Alan | Değer |
| --- | --- |
| `id` | `2` |
| `event_uid` | `paperclip:run:kosu-0009:finished` |
| `schema_version` | `2` |
| `occurred_at` | `2026-11-28T09:14:02.000Z` |
| `time_basis` | `source` |
| `observed_after` | boş |
| `recorded_at` | `2026-11-28T09:15:40.000Z` |
| `source` | `paperclip` |
| `source_ref` | `kosu-0009` |
| `action` | `run.finished` |
| `actor_kind` | `agent` |
| `actor_id` | `ajan-0007` |
| `actor_role` | `developer` |
| `team` | `team_b` |
| `account_ref` | `claude-03` |
| `account_certainty` | `pool_order` |
| `model` | `claude-opus-5-5` |
| `issue_id` | `is-0042` |
| `run_id` | `kosu-0009` |
| `pr_ref` | `ornek/depo#42` |
| `requirement_id` | boş |
| `correlation_id` | `is-0001` |
| `causation_id` | boş |
| `outcome` | `failed` |
| `source_code` | `adapter_failed` |
| `corrects_event_uid` | boş |
| `payload` | `{"status":"failed","errorCode":"adapter_failed","exitCode":1,"retryOfRunId":null}` |
| `prev_hash` | `0871334d18db5bb33511878c15ae81572f36bb6846aa8616fa3eb13b85a22dca` |

### Satırın iki bağı

Bağlar burada yazılma sırasıyla durur.

| `object_kind` | `object_id` | `link_basis` | `recorded_at` |
| --- | --- | --- | --- |
| `issue` | `is-0050` | `inferred` | `2026-11-28T09:15:40.000Z` |
| `agent` | `ajan-0011` | `explicit` | `2026-11-28T09:15:40.000Z` |

### Çıkan özet metni

Metin tek satırdır. Metnin sonunda satır sonu yoktur.

```json
{"account_certainty":"pool_order","account_ref":"claude-03","action":"run.finished","actor_id":"ajan-0007","actor_kind":"agent","actor_role":"developer","causation_id":null,"corrects_event_uid":null,"correlation_id":"is-0001","event_uid":"paperclip:run:kosu-0009:finished","id":2,"issue_id":"is-0042","model":"claude-opus-5-5","objects":[{"link_basis":"explicit","object_id":"ajan-0011","object_kind":"agent","recorded_at":"2026-11-28T09:15:40.000Z"},{"link_basis":"inferred","object_id":"is-0050","object_kind":"issue","recorded_at":"2026-11-28T09:15:40.000Z"}],"observed_after":null,"occurred_at":"2026-11-28T09:14:02.000Z","outcome":"failed","payload":{"errorCode":"adapter_failed","exitCode":1,"retryOfRunId":null,"status":"failed"},"pr_ref":"ornek/depo#42","prev_hash":"0871334d18db5bb33511878c15ae81572f36bb6846aa8616fa3eb13b85a22dca","recorded_at":"2026-11-28T09:15:40.000Z","requirement_id":null,"run_id":"kosu-0009","schema_version":2,"source":"paperclip","source_code":"adapter_failed","source_ref":"kosu-0009","team":"team_b","time_basis":"source"}
```

### Çıkan özet

Bu değer satırın `row_hash` alanına yazılır.

```text
8373532f33ed00e854a2ea6329c81bbe73da1aa2953689b7e4be484859a1a35e
```

### Örnekte görülen kurallar

- Dört boş zarf alanı `null` diye yazıldı.
- `agent` bağı `issue` bağından önce yazıldı.
- `payload` içinde `errorCode` anahtarı `status` anahtarından önce yazıldı.
- `prev_hash` değeri 1. satırın özetidir.

### Örnek nasıl denetlenir?

1. Özet metnini bir dosyaya kaydedin. Dosya UTF-8 olsun. Dosyanın sonunda satır sonu olmasın.
2. Dosyanın SHA-256 değerini hesaplayın.
3. Çıkan değer yukarıdaki özetle aynı olmalıdır.
