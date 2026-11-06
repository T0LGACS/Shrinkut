# Shrinkut

Videoları kayıpsız kes, istediğin boyuta sıkıştır. Discord'un dosya sınırına sığdırmak için yapıldı.

**[⬇ Son sürümü indir (Shrinkut.exe)](../../releases/latest/download/Shrinkut.exe)**

Kurulum yok: indir, çift tıkla. FFmpeg içinde geliyor. Yeni sürüm çıkınca uygulama üstte "Güncelle" düğmesi gösterir.

## Neler yapıyor

- **Kes (kayıpsız):** Zaman çizelgesindeki tutamaçları sürükle; video yeniden kodlanmadan, saniyeler içinde kesilir.
- **Sıkıştır:** Hedef boyutu yaz (ör. 490 MB). Varsa NVIDIA / AMD / Intel ekran kartını kullanır, yoksa işlemciyle sıkıştırır.
- Önizleme, kare şeridi, ilerleme yüzdesi ve kalan süre, iptal, sürükle-bırak.

Windows ilk açılışta "tanınmayan uygulama" uyarısı verebilir: **Ek bilgi → Yine de çalıştır**.

## Gizlilik

Shrinkut videolarını yalnızca senin bilgisayarında işler; hiçbir dosyanı ya da kişisel bilgini bir yere göndermez.

Tek ağ bağlantısı güncelleme denetimidir: İzin verirsen her açılışta `api.github.com` adresinden son sürümün numarasını sorar, "Güncelle"ye basarsan yeni sürümü GitHub'dan indirir. İlk açılışta izin istenir, pencerenin altındaki kutucuktan istediğin zaman kapatabilirsin. Bu istekler [GitHub'ın gizlilik bildirimine](https://docs.github.com/site-policy/privacy-policies/github-general-privacy-statement) tabidir.

*This program will not transfer any information to other networked systems unless specifically requested by the user, except for the optional update check (asked on first start, can be turned off at any time), which requests the latest version number from api.github.com.*

## Kod imzalama politikası (Code signing policy)

Free code signing provided by [SignPath.io](https://about.signpath.io), certificate by [SignPath Foundation](https://signpath.org).

İmzalı sürümler, SignPath Foundation başvurusu onaylandıktan sonra yayınlanacaktır. Her `.exe`, bu depodaki kaynak koddan GitHub Actions ile otomatik derlenir; elle derlenmiş dosya imzalanmaz.

- **Yazarlar ve gözden geçirenler (Committers and reviewers):** [T0LGACS](https://github.com/T0LGACS)
- **İmza onaylayıcı (Approvers):** [T0LGACS](https://github.com/T0LGACS)

## Lisans

Shrinkut [GPLv3](LICENSE) lisanslıdır ve GPLv3 lisanslı [FFmpeg](https://ffmpeg.org) içerir.
