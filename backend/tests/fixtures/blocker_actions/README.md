# Engel eylemleri için sahte veri

Bu klasör AJA-2312 işinde yazıldı. Kaynak AJA-2145 tasarım belgesinin 4.1, 4.3 ve 4.5 bölümüdür.

Bu veri sahtedir. Veri gerçek kayıttan alınmadı. Veride gerçek ajan adı, gizli bilgi ve canlı adres yoktur.

## Dosyalar

| Dosya | İçinde ne var? |
| --- | --- |
| `cases.json` | On beş durumun girdisi. |
| `fake_paperclip.json` | Sahte Paperclip yanıtları. |
| `expected_events.json` | On beş durumun beklenen sonucu ve defter olayları. |

Testi `backend/tests/test_blocker_actions_fixtures.py` dosyası koşar.

## On beş durum

| No | Durum | Beklenen sonuç |
| --- | --- | --- |
| 1 | `local` kullanıcı yedi eylem düğmesine birer kez basar. | Yedi istek açılır. Hepsi `done` olur. |
| 2 | Tailscale kullanıcısı bir düğmeye basar. | Yanıt `403` olur. Deftere yalnız `action.denied` yazılır. |
| 3 | `Origin` başlığı farklı olan istek gelir. | Yanıt `403` olur. Satır ve olay açılmaz. |
| 4 | Aynı düğmeye iki kez basılır. | Tek istek açılır. İkinci yanıt ilk isteği döner. |
| 5 | Durdurulmuş ajana "Ajanı uyandır" denir. | Sonuç `denied` olur. |
| 6 | Çalışan koşusu olan ajana "Ajanı uyandır" denir. | Sonuç `skipped_state_changed` olur. |
| 7 | Açık işi olmayan ajana "Ajanı uyandır" denir. | Sonuç `skipped_state_changed` olur. Ajan uyandırılmaz. |
| 8 | Durdurulmuş sahip için "Sahibine ver" denir. | Sonuç `denied` olur. |
| 9 | Başka takımdaki ajana "Başka ajana ver" denir. | İş o takımın PO ajanına verilir. |
| 10 | "Müşteriye sor" basılır. | Kart açılır. Sorunun metni deftere yazılmaz. |
| 11 | Kökün Paperclip işi yokken "Müşteriye sor" basılır. | Önce "Karar sorusu" işi açılır. Kart bu işe eklenir. |
| 12 | "Müşteriye sor" düğmesine üç kez basılır. | Tek istek ve tek kart açılır. |
| 13 | Açık Kaizen adayı varken "Kaizen adayı yap" basılır. | Yalnız kanıt eklenir. |
| 14 | "Kök nedeni kaydet" sözlükte olmayan kodla basılır. | Yanıt `400` olur. Satır ve olay açılmaz. |
| 15 | "Paperclip'te aç" ve "GitHub'da aç" basılır. | Backend'e istek gitmez. Deftere olay yazılmaz. |

12. durumda ikinci basış RTE sonucu bildirmeden önce gelir. Üçüncü basış kart açıldıktan sonra gelir. İki basışta da backend ilk isteği döner.

## Girdi nasıl okunur?

`cases.json` dosyasının başında ortak ayarlar vardır.

- `board_origin` alanı panonun kendi adresidir. Backend `Origin` başlığını bu değerle karşılaştırır.
- `permissions` alanı izin listesidir. `local` kullanıcı yedi eylemi yapar. Tailscale kullanıcısı hiçbir eylemi yapamaz.
- `root_cause_codes` alanı sahte sözlüktür. Bu liste gerçek sözlüğün bir parçasıdır.

Her durumun şu girdileri vardır.

- `blocker` alanı engeli verir. Bu bilgiyi gerçekte engel tablosu hesaplar. Bu veri o hesabı denemez.
- `presses` alanı düğme basışlarını sırayla verir. Her basışta kullanıcı, `Origin` başlığı ve istek gövdesi vardır.
- `link` değeri `true` olan basış yalnız bağlantıdır. Bu basış backend'e istek göndermez.
- `rte_reports` alanı RTE'nin sonucu bildirdiği anı verir.
- `first_request_id` alanı ilk açılan isteğin kimliğidir. Sonraki istekler birer artar.
- `kaizen_items` alanı testten önce açık olan Kaizen adaylarını verir.
- `resolved_interaction_ids` alanı kapanmış soru kartlarını verir. Liste boşsa kart açık sayılır.

## Sahte Paperclip nasıl okunur?

`fake_paperclip.json` dosyasında her durumun kendi yanıt listesi vardır. Anahtar, isteğin yöntemi ve yoludur. Örneğin `GET /api/agents/agent-demo-dev-5` anahtarı ajanın durumunu verir.

- Ajan yanıtı ajanın durumunu verir. Değer `idle`, `running` ya da `paused` olur.
- `live-runs` yanıtı çalışan koşuları verir.
- `issues?assigneeAgentId=` yanıtı ajanın işlerini verir.
- Takım ajanın adından çıkar. Örneğin "Team X Demo Dev 1" adı `team_x` olur.

Sahte yanıtlar sabittir. Bir yazma isteği sonraki okuma yanıtını değiştirmez.

## Beklenen sonuç nasıl okunur?

Her durumun beş sonucu vardır.

- `responses` alanı her basışın yanıtını verir. `created` değeri `true` ise yeni satır açılmıştır.
- `action_requests` alanı `action_request` satırlarının son halini verir.
- `rte` alanı RTE'nin bildirdiği sonucu ve Paperclip'e yazdığı istekleri verir.
- `ledger_events` alanı deftere yazılan olayları sırayla verir.
- `kaizen_events` alanı Kaizen akışının yazdığı olayları verir.

Satırdaki `dedupe` alanı tekil anahtarın dört parçasını verir. Yetkisiz isteğin satırında bu alan boştur. Çünkü o satır tekil anahtara girmez.

Satırdaki `listed_in_due` alanı satırın `GET /api/actions/due` listesine girip girmediğini söyler. Yetkisiz istek ve "Kök nedeni kaydet" isteği bu listeye girmez.

## Defter olayları

Zarf AJA-2140 tasarımının 1.2 bölümündeki zarftır. Olay adları AJA-2145 tasarımının 4.5 bölümündeki dört addır.

| Olay | `event_uid` örneği |
| --- | --- |
| `action.requested` | `safeboard:action_request:101:requested` |
| `action.denied` | `safeboard:action_request:201:denied` |
| `action.completed` | `safeboard:action_request:101:completed` |
| `blocker.root_cause_recorded` | `safeboard:action_request:107:root_cause_recorded` |

- `source_ref` alanı istek kimliğidir.
- `action.completed` olayının `causation_id` alanı aynı isteğin `action.requested` olayını gösterir.
- "Kök nedeni kaydet" üç olay yazar. Üç olayın zamanı aynıdır.
- Defter satırında özet alanları yoktur. `prev_hash` ve `row_hash` değerini defter yazan kod hesaplar.

## Bu verinin kapsamadığı yerler

Tasarımın 4. bölümü bazı ayrıntıları yazmıyor. Bu veri o ayrıntıları uydurmaz.

- `escalate_next` ve `kaizen_candidate` için `paperclip_writes` alanı boştur. Bu yazmaları başka akışlar tanımlar.
- `escalation.sent` olayı bu veride yoktur. Bu olay başka bir tasarımın olayıdır.
- Kaizen olaylarında `event_uid` yoktur. Olay `kaizen_key` alanıyla tanınır.
- Hata metinleri örnektir. Test yalnız yanıt kodunu ve gövdenin biçimini denetler.

Üç nokta geliştiricinin okumasıdır. Kod yazan kişi bu noktaları tasarım sahibine doğrulatmalıdır.

- Aynı düğmeye ikinci basışta yanıt kodu `202` olur.
- `source_ref` alanı metin olarak yazılır. Örneğin `"101"`.
- "Kök nedeni kaydet" olaylarında aktör düğmeye basan kullanıcıdır.
