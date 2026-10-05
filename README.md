# xray

☬SHΞN™ idea core v2ray spellier tool

---

# گردآورندهٔ ساعتی VLESS

این مخزن هر ساعت فهرست کانفیگ‌های عمومی VLESS را از ۲۴ خوراک خام دریافت می‌کند، VLESSهای پشتیبانی‌شده را جدا می‌کند، موارد تکراری را کنار می‌گذارد، فقط اتصال TCP به آدرس‌های عمومی را می‌آزماید و کانفیگ‌های پاسخ‌گو را در `vless.txt` می‌نویسد. نام نمایشی تمام خروجی‌ها `T.me/aShervin` است.

## راه‌اندازی در GitHub

1. فایل‌های این بسته را در یک مخزن عمومی GitHub بارگذاری کنید و شاخهٔ پیش‌فرض را `main` بگذارید.
2. در تنظیمات مخزن، بخش **Actions → General → Workflow permissions** را باز کنید و اجازهٔ نوشتن محتوا را فعال کنید. ورک‌فلو نیز `contents: write` درخواست می‌کند.
3. از زبانهٔ **Actions**، ورک‌فلو **Update VLESS subscription** را یک‌بار با **Run workflow** اجرا کنید. پس از اجرای موفق، `vless.txt` در ریشهٔ شاخهٔ اصلی ساخته یا به‌روزرسانی می‌شود؛ سپس زمان‌بندی هر ساعت آن را تازه می‌کند.
4. لینک سابسکریپشن، پس از عمومی‌شدن مخزن، این است:

   `https://raw.githubusercontent.com/aishervin/xray/main/vless.txt`

   این لینک فایل `vless.txt` در مخزن `aishervin/xray` را می‌خواند.

## افزودن یا حذف منبع

هر خط از `source/source.txt` یک نشانی HTTPS برای فایل متنی/سابسکریپشن عمومی است. اسکریپت همین فایل را در هر اجرا می‌خواند؛ برای تغییر منابع، همین فایل را ویرایش و تغییر را به GitHub بفرستید. خطوط خالی و خطوطی که با `#` شروع شوند نادیده گرفته می‌شوند. برای رعایت حق و شرایط استفادهٔ ناشران، فقط از خوراک‌های عمومی و مجاز استفاده کنید.

منابع انتخاب‌شده (تعداد ستاره‌ها تقریبی و مطابق صفحات بررسی‌شده در ۵ اکتبر ۲۰۲۶ است):

| مخزن | ستارهٔ تقریبی | خوراک مورد استفاده |
|---|---:|---|
| [Epodonios/v2ray-configs](https://github.com/Epodonios/v2ray-configs) | 3.3k | [VLESS](https://raw.githubusercontent.com/Epodonios/v2ray-configs/main/Splitted-By-Protocol/vless.txt) |
| [barry-far/V2ray-Config](https://github.com/barry-far/V2ray-Config) | 2.5k | [VLESS](https://raw.githubusercontent.com/barry-far/V2ray-Config/main/Splitted-By-Protocol/vless.txt) |
| [ebrasha/free-v2ray-public-list](https://github.com/ebrasha/free-v2ray-public-list) | 1.3k | [VLESS](https://raw.githubusercontent.com/ebrasha/free-v2ray-public-list/refs/heads/main/vless_configs.txt) |
| [0xRadikal/Free-v2ray-Configs](https://github.com/0xRadikal/Free-v2ray-Configs) | 679 | [فهرست بررسی‌شده](https://raw.githubusercontent.com/0xRadikal/Free-v2ray-Configs/main/verified/configs.txt) |
| [MatinGhanbari/v2ray-configs](https://github.com/MatinGhanbari/v2ray-configs) | 676 | [VLESS](https://raw.githubusercontent.com/MatinGhanbari/v2ray-configs/main/subscriptions/filtered/subs/vless.txt) |
| [Delta-Kronecker/V2ray-Config](https://github.com/Delta-Kronecker/V2ray-Config) | 349 | [VLESS](https://raw.githubusercontent.com/Delta-Kronecker/V2ray-Config/main/config/protocols/vless.txt) |
| [MhdiTaheri/V2rayCollector](https://github.com/MhdiTaheri/V2rayCollector) | 321 | [خروجی VLESS](https://raw.githubusercontent.com/MhdiTaheri/V2rayCollector/main/sub/vless) |
| [hamedcode/port-based-v2ray-configs](https://github.com/hamedcode/port-based-v2ray-configs) | 133 | [VLESS](https://raw.githubusercontent.com/hamedcode/port-based-v2ray-configs/main/sub/vless.txt) |
| [MahanKenway/Freedom-V2Ray](https://github.com/MahanKenway/Freedom-V2Ray) | 113 | [VLESS](https://raw.githubusercontent.com/MahanKenway/Freedom-V2Ray/main/configs/vless.txt) |
| [rtwo2/FastNodes](https://github.com/rtwo2/FastNodes) | 94 | [VLESS](https://raw.githubusercontent.com/rtwo2/FastNodes/main/sub/protocols/vless.txt) |

خوراک‌های تکمیلی که در این نوبت بررسی و اضافه شدند:

| مخزن | خوراک |
|---|---|
| [aishervin/V2flair](https://github.com/aishervin/V2flair) | [clean_sub.txt](https://raw.githubusercontent.com/aishervin/V2flair/refs/heads/main/clean_sub.txt) |
| [aishervin/subfine](https://github.com/aishervin/subfine) | [sub.txt](https://raw.githubusercontent.com/aishervin/subfine/refs/heads/main/sub.txt) |
| [aishervin/v2ray](https://github.com/aishervin/v2ray) | [Sub.json](https://raw.githubusercontent.com/aishervin/v2ray/refs/heads/main/Sub.json) |
| [0xRadikal/Free-v2ray-Configs](https://github.com/0xRadikal/Free-v2ray-Configs) | [all/configs.txt](https://raw.githubusercontent.com/0xRadikal/Free-v2ray-Configs/refs/heads/main/all/configs.txt) |
| [iboxz/free-v2ray-collector](https://github.com/iboxz/free-v2ray-collector) | [vless.txt](https://raw.githubusercontent.com/iboxz/free-v2ray-collector/main/main/vless.txt) |
| [igareck/vpn-configs-for-russia](https://github.com/igareck/vpn-configs-for-russia) | [Vless-Reality-White-Lists-Rus-Mobile.txt](https://raw.githubusercontent.com/igareck/vpn-configs-for-russia/refs/heads/main/Vless-Reality-White-Lists-Rus-Mobile.txt) |
| [F0rc3Run/F0rc3Run](https://github.com/F0rc3Run/F0rc3Run) | [VLESS](https://raw.githubusercontent.com/F0rc3Run/F0rc3Run/refs/heads/main/splitted-by-protocol/vless.txt) |
| [barry-far/V2ray-Config](https://github.com/barry-far/V2ray-Config) | [Sub1.txt](https://raw.githubusercontent.com/barry-far/V2ray-config/refs/heads/main/Sub1.txt) |
| [ebrasha/free-v2ray-public-list](https://github.com/ebrasha/free-v2ray-public-list) | [V2Ray-Config-By-EbraSha.txt](https://raw.githubusercontent.com/ebrasha/free-v2ray-public-list/refs/heads/main/V2Ray-Config-By-EbraSha.txt) |
| [ALIILAPRO/v2rayNG-Config](https://github.com/ALIILAPRO/v2rayNG-Config) | [sub.txt](https://raw.githubusercontent.com/ALIILAPRO/v2rayNG-Config/refs/heads/main/sub.txt) |
| [MatinGhanbari/v2ray-configs](https://github.com/MatinGhanbari/v2ray-configs) | [all_sub.txt](https://raw.githubusercontent.com/MatinGhanbari/v2ray-configs/main/subscriptions/v2ray/all_sub.txt) |
| [Epodonios/v2ray-configs](https://github.com/Epodonios/v2ray-configs) | [All_Configs_Sub.txt](https://raw.githubusercontent.com/Epodonios/v2ray-configs/refs/heads/main/All_Configs_Sub.txt) |
| [Farid-Karimi/Config-Collector](https://github.com/Farid-Karimi/Config-Collector) | [vless_iran.txt](https://raw.githubusercontent.com/Farid-Karimi/Config-Collector/main/vless_iran.txt) |
| [MohammadBahemmat/V2ray-Collector](https://github.com/MohammadBahemmat/V2ray-Collector) | [servers/vless_servers.txt](https://raw.githubusercontent.com/MohammadBahemmat/V2ray-Collector/main/servers/vless_servers.txt) |

هر ۱۴ خوراک تکمیلی هنگام بررسی با کد HTTP `200` پاسخ دادند و در محتوای مستقیم یا Base64 آن‌ها VLESS پیدا شد. تعدادی از نشانی‌های ارسالی 404 بودند یا فقط VMess/Hysteria2 داشتند؛ برای اینکه منبع بی‌استفاده و خطای زمان‌بندی اضافه نشود، وارد فهرست VLESS نشدند. وضعیت و دسترس‌پذیری منابع ممکن است تغییر کند. برخی خوراک‌ها ترکیبی یا Base64 هستند و اسکریپت VLESS را از آن‌ها استخراج می‌کند.

## فیلترها و بررسی اتصال

- انتقال‌های `ws`/`websocket`، `grpc`، `xhttp`، `http`، `httpupgrade` و `h2` پذیرفته می‌شوند.
- کانفیگ‌های `security=reality` نیز پذیرفته می‌شوند، حتی اگر انتقال آن‌ها TCP باشد؛ در VLESS، Reality یک لایهٔ امنیتی است، نه نوع انتقال.
- نام گره، ترتیب پارامترهای URL و تفاوت حروف میزبان در حذف تکراری‌ها لحاظ نمی‌شوند.
- پورت هر گره با اتصال TCP آزمایش می‌شود. آدرس‌های خصوصی، loopback و رزروشده عمداً امتحان نمی‌شوند.
- پاسخ TCP فقط نشان می‌دهد پورت در آن لحظه اتصال را قبول کرده است؛ اتصال کامل VLESS، سرعت، حریم خصوصی یا امنیت را تضمین نمی‌کند.
- سقف پیش‌فرض ورک‌فلو ۵۰٬۰۰۰ کانفیگ برای هر اجراست. متغیرهای `MAX_CONFIGS`، `TCP_WORKERS` و `TCP_TIMEOUT` در ورک‌فلو قابل تغییرند. اگر همهٔ منابع خراب شوند یا هیچ کانفیگ قابل‌خواندنی ندهند، خروجی سالم قبلی حفظ می‌شود.

## اجرای محلی و آزمون

نیازی به نصب بستهٔ پایتون نیست؛ فقط Python 3.10 یا جدیدتر لازم است.

```bash
python -m unittest discover -s tests -v
python collector.py
```

## نکات امنیتی و پایداری

این مخزن فقط پیکربندی‌های عمومیِ اشخاص ثالث را تجمیع می‌کند و هیچ سروری را اداره یا تأیید نمی‌کند. اپراتور هر سرور می‌تواند فرادادهٔ اتصال و ترافیک شما را ببیند؛ برای حساب‌ها، پرداخت‌ها یا اطلاعات حساس از گره ناشناس استفاده نکنید. استفاده از سرویس‌های عمومی ممکن است با قوانین یا شرایط ناشر سازگار نباشد؛ مسئولیت بررسی و استفاده بر عهدهٔ کاربر است.

زمان‌بندی GitHub Actions ممکن است زیر بار سرویس با تأخیر اجرا شود و برای اجرا به شاخهٔ پیش‌فرض نیاز دارد. برای تازه‌سازی فوری، از **Actions → Run workflow** استفاده کنید.
