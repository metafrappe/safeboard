# 0001: MVP panosu repoya taşındı

Bu karar 27 Kasım 2026 Cuma günü AJA-2049 işinde verildi.

## Karar

MVP panosu bu repoya taşındı. Taşıma sırasında davranış değişmedi.

Mimari karar AJA-2028 belgesindedir. Klasör yapısı bu karara uyar.

## Ne nereye gitti

- `server.py` dosyası parçalara bölündü.
  - Paperclip okuma kodu `backend/safeboard/collect/paperclip.py` dosyasına gitti.
  - GitHub okuma kodu `backend/safeboard/collect/github.py` dosyasına gitti.
  - Pano özeti `backend/safeboard/flow/board.py` dosyasına gitti.
  - Burndown hesabı `backend/safeboard/flow/burndown.py` dosyasına gitti.
  - Sprint ayarı `backend/safeboard/pi/sprint.py` dosyasına gitti.
  - HTTP sunucusu `backend/safeboard/web/server.py` dosyasına gitti.
- `index.html` dosyası `frontend/index.html` yoluna aynen taşındı. Vite bu dosyayı derler.
- `sprint.json` repoya girmedi. Dosya artık veri klasöründe durur.

## Değişen küçük şeyler

- Yazı tipi artık `@fontsource-variable/outfit` paketinden gelir. Eski yol başka bir repoya bağlıydı.
- Ayarlar ortam değişkeniyle değişir. Varsayılan değerler MVP ile aynıdır.
- Hiç çalışmayan bir kod satırı silindi. Bu satır burndown hesabında bir şey yapmıyordu.

## Bilinen eski kusur

Sayfa 320 piksel genişlikte yatay taşıyor. Bu kusur MVP'de de vardı. Taşıma davranışı değiştirmemeliydi. Bu yüzden kusur bu işte düzeltilmedi.

## Sonraki işler

- Testleri test epiği yazar. Bu projede testler en sonda yazılır (AJA-2077).
- Mimari karar `safeboard.toml` ayar dosyasından söz eder. Python 3.9 sürümünde TOML okuyucu yoktur. Bu yüzden şimdilik ortam değişkenleri kullanılır.
