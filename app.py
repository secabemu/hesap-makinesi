from flask import Flask, render_template, request, jsonify
import math, webbrowser, time, ssl, urllib.request, json

app = Flask(__name__)

# ── Önbellekler ───────────────────────────────────────────────────
_kur_cache   = {}
_kur_zaman   = 0
_altin_cache = {}
_altin_zaman = 0
CACHE_SURE   = 120
SSL_CTX      = ssl._create_unverified_context()

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

# ══════════════════════════════════════════════════════════════════
#  DÖVİZ
# ══════════════════════════════════════════════════════════════════
def kurlari_getir():
    global _kur_cache, _kur_zaman
    if _kur_cache.get("USD") and (time.time() - _kur_zaman) < CACHE_SURE:
        return _kur_cache

    # yfinance
    try:
        import yfinance as yf
        usd = yf.Ticker("USDTRY=X").fast_info["last_price"]
        eur = yf.Ticker("EURTRY=X").fast_info["last_price"]
        _kur_cache = {"USD": round(usd,4), "EUR": round(eur,4),
                      "tarih": time.strftime("%Y-%m-%d"), "kaynak": "Yahoo"}
        _kur_zaman = time.time()
        print(f"✔ Döviz (yfinance): USD={usd:.4f} EUR={eur:.4f}")
        return _kur_cache
    except Exception as e:
        print(f"✗ yfinance: {e}")

    # Frankfurter fallback
    try:
        req = urllib.request.Request(
            "https://api.frankfurter.app/latest?from=TRY&to=USD,EUR",
            headers=HEADERS)
        with urllib.request.urlopen(req, timeout=6, context=SSL_CTX) as r:
            d = json.loads(r.read())
        _kur_cache = {"USD": round(1/d["rates"]["USD"],4),
                      "EUR": round(1/d["rates"]["EUR"],4),
                      "tarih": d["date"], "kaynak": "Frankfurter"}
        _kur_zaman = time.time()
        print(f"✔ Döviz (frankfurter): USD={_kur_cache['USD']} EUR={_kur_cache['EUR']}")
        return _kur_cache
    except Exception as e:
        print(f"✗ frankfurter: {e}")

    if not _kur_cache.get("USD"):
        _kur_cache = {"USD": None, "EUR": None, "tarih": "bağlantı yok", "kaynak": "yok"}
    return _kur_cache


# ══════════════════════════════════════════════════════════════════
#  ALTIN — altinkaynak.com
# ══════════════════════════════════════════════════════════════════
def altin_getir():
    global _altin_cache, _altin_zaman
    if _altin_cache.get("gram24") and (time.time() - _altin_zaman) < CACHE_SURE:
        return _altin_cache

    # ── Yöntem 1: altinkaynak.com ─────────────────────────────────
    try:
        from bs4 import BeautifulSoup
        req = urllib.request.Request(
            "https://www.altinkaynak.com/Altin/Kur/Cesitleri",
            headers=HEADERS)
        with urllib.request.urlopen(req, timeout=8, context=SSL_CTX) as r:
            soup = BeautifulSoup(r.read(), "html.parser")

        sonuc = {}
        for satir in soup.select("table tr"):
            hucreler = satir.select("td")
            if len(hucreler) < 3:
                continue
            isim = hucreler[0].get_text(strip=True).lower()
            fiyat_str = hucreler[2].get_text(strip=True).replace(".", "").replace(",", ".")
            try:
                fiyat = float(fiyat_str)
            except:
                continue

            if "gram" in isim and "24" in isim:
                sonuc["gram24"] = fiyat
            elif "gram" in isim and "22" in isim:
                sonuc["gram22"] = fiyat
            elif "gram" in isim and ("18" in isim or "14" in isim):
                sonuc["gram18"] = fiyat
            elif "cumhuriyet" in isim:
                sonuc["cumhuriyet"] = fiyat
            elif "çeyrek" in isim or "ceyrek" in isim:
                sonuc["ceyrek"] = fiyat
            elif "yarım" in isim or "yarim" in isim:
                sonuc["yarim"] = fiyat

        if sonuc.get("gram24"):
            sonuc["tarih"]  = time.strftime("%H:%M")
            sonuc["kaynak"] = "altinkaynak.com"
            _altin_cache = sonuc
            _altin_zaman = time.time()
            print(f"✔ Altın (altinkaynak): 24ayar={sonuc.get('gram24')} 22ayar={sonuc.get('gram22')}")
            return _altin_cache
        else:
            print("✗ altinkaynak: veri parse edilemedi, fallback deneniyor")
    except Exception as e:
        print(f"✗ altinkaynak: {e}")

    # ── Yöntem 2: bigpara.com ─────────────────────────────────────
    try:
        from bs4 import BeautifulSoup
        req = urllib.request.Request(
            "https://bigpara.hurriyet.com.tr/altin/",
            headers=HEADERS)
        with urllib.request.urlopen(req, timeout=8, context=SSL_CTX) as r:
            soup = BeautifulSoup(r.read(), "html.parser")

        sonuc = {}
        for satir in soup.select("tbody tr"):
            hucreler = satir.select("td")
            if len(hucreler) < 2:
                continue
            isim = hucreler[0].get_text(strip=True).lower()
            fiyat_str = hucreler[1].get_text(strip=True).replace(".", "").replace(",", ".")
            try:
                fiyat = float(fiyat_str)
            except:
                continue

            if "gram" in isim and ("24" in isim or "has" in isim):
                sonuc["gram24"] = fiyat
            elif "gram" in isim and "22" in isim:
                sonuc["gram22"] = fiyat
            elif "çeyrek" in isim or "ceyrek" in isim:
                sonuc["ceyrek"] = fiyat
            elif "cumhuriyet" in isim or "tam" in isim:
                sonuc["cumhuriyet"] = fiyat

        if sonuc.get("gram24"):
            sonuc["tarih"]  = time.strftime("%H:%M")
            sonuc["kaynak"] = "bigpara.com"
            _altin_cache = sonuc
            _altin_zaman = time.time()
            print(f"✔ Altın (bigpara): 24ayar={sonuc.get('gram24')}")
            return _altin_cache
    except Exception as e:
        print(f"✗ bigpara: {e}")

    # ── Yöntem 3: yfinance ile altın (XAU/USD → TL) ──────────────
    try:
        import yfinance as yf
        xau_usd = yf.Ticker("GC=F").fast_info["last_price"]   # ons fiyatı
        usd_try = kurlari_getir().get("USD") or 0
        if xau_usd and usd_try:
            gram24 = round((xau_usd / 31.1035) * usd_try, 2)   # 1 ons = 31.1g
            gram22 = round(gram24 * (22/24), 2)
            gram18 = round(gram24 * (18/24), 2)
            sonuc  = {
                "gram24":     gram24,
                "gram22":     gram22,
                "gram18":     gram18,
                "ceyrek":     round(gram24 * 1.75, 2),
                "yarim":      round(gram24 * 3.5,  2),
                "cumhuriyet": round(gram24 * 7.0,  2),
                "tarih":      time.strftime("%H:%M"),
                "kaynak":     "Yahoo (hesaplanmış)"
            }
            _altin_cache = sonuc
            _altin_zaman = time.time()
            print(f"✔ Altın (yfinance hesap): 24ayar={gram24}")
            return _altin_cache
    except Exception as e:
        print(f"✗ yfinance altin: {e}")

    if not _altin_cache.get("gram24"):
        _altin_cache = {"hata": "Altın verisi alınamadı", "tarih": "—", "kaynak": "yok"}
    return _altin_cache


# ══════════════════════════════════════════════════════════════════
#  FLASK ROUTE'LAR
# ══════════════════════════════════════════════════════════════════
@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/kur")
def kur():
    return jsonify(kurlari_getir())

@app.route("/api/altin")
def altin():
    return jsonify(altin_getir())

@app.route("/hesapla", methods=["POST"])
def hesapla():
    data  = request.json
    islem = data.get("islem")
    a_str = data.get("a", "")
    b_str = data.get("b", "")
    try:
        a = float(a_str) if a_str != "" else None
        b = float(b_str) if b_str != "" else None
        if   islem == "toplama":    sonuc = a + b
        elif islem == "cikarma":    sonuc = a - b
        elif islem == "carpma":     sonuc = a * b
        elif islem == "bolme":
            if b == 0: return jsonify({"hata": "Sıfıra bölme hatası!"})
            sonuc = a / b
        elif islem == "mod":
            if b == 0: return jsonify({"hata": "Sıfıra mod hatası!"})
            sonuc = a % b
        elif islem == "us":         sonuc = a ** b
        elif islem == "karekök":
            if a < 0: return jsonify({"hata": "Negatif sayının karekökü alınamaz!"})
            sonuc = math.sqrt(a)
        elif islem == "kare":       sonuc = a ** 2
        elif islem == "kup":        sonuc = a ** 3
        elif islem == "ters":
            if a == 0: return jsonify({"hata": "Sıfırın tersi tanımsız!"})
            sonuc = 1 / a
        elif islem == "abs":        sonuc = abs(a)
        elif islem == "faktöriyel":
            if a < 0 or a != int(a): return jsonify({"hata": "Pozitif tam sayı girin!"})
            if a > 170:              return jsonify({"hata": "Sayı çok büyük!"})
            sonuc = math.factorial(int(a))
        elif islem == "log":
            if a <= 0: return jsonify({"hata": "Log için pozitif sayı girin!"})
            sonuc = math.log10(a)
        elif islem == "ln":
            if a <= 0: return jsonify({"hata": "Ln için pozitif sayı girin!"})
            sonuc = math.log(a)
        elif islem == "sin":        sonuc = math.sin(math.radians(a))
        elif islem == "cos":        sonuc = math.cos(math.radians(a))
        elif islem == "tan":        sonuc = math.tan(math.radians(a))
        else: return jsonify({"hata": "Bilinmeyen işlem!"})

        if isinstance(sonuc, float) and sonuc.is_integer(): sonuc = int(sonuc)
        elif isinstance(sonuc, float): sonuc = round(sonuc, 8)
        return jsonify({"sonuc": sonuc})
    except Exception as e:
        return jsonify({"hata": str(e)})


if __name__ == "__main__":
    print("Veriler yükleniyor...")
    kurlari_getir()
    altin_getir()
    webbrowser.open("http://127.0.0.1:5000")
    app.run(debug=False)
