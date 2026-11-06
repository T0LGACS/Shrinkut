# Shrinkut

Videoları kayıpsız kes, istediğin boyuta sıkıştır. Discord'un dosya sınırına sığdırmak için yapıldı.

**[⬇ Son sürümü indir (Shrinkut.exe)](../../releases/latest/download/Shrinkut.exe)**

Kurulum yok: indir, çift tıkla. FFmpeg içinde geliyor. Yeni sürüm çıkınca uygulama üstte "Güncelle" düğmesi gösterir.

## Neler yapıyor

- **Kes (kayıpsız):** Zaman çizelgesindeki tutamaçları sürükle; video yeniden kodlanmadan, saniyeler içinde kesilir.
- **Sıkıştır:** Hedef boyutu yaz (ör. 490 MB). Varsa NVIDIA / AMD / Intel ekran kartını kullanır, yoksa işlemciyle sıkıştırır.
- Önizleme, kare şeridi, ilerleme yüzdesi ve kalan süre, iptal, sürükle-bırak.

Windows ilk açılışta "tanınmayan uygulama" uyarısı verebilir: **Ek bilgi → Yine de çalıştır**.

## Geliştirme

```bash
pip install -r requirements.txt
python app.py
```

Yeni sürüm yayınlamak için `yayinla.bat` çalıştır ve sürüm numarasını yaz; GitHub `.exe`'yi kendisi derleyip yayınlar.

Shrinkut, GPLv3 lisanslı [FFmpeg](https://ffmpeg.org) içerir.
