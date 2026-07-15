"""Vonatverseny API — 3. változat: a haladás az ADATBÁZISBAN él.

Újdonságok a 2. változathoz képest:
  - PostgreSQL-kapcsolat (a Supabase adatbázisához)
  - GET  /api/save        — a játékos mentett állása
  - POST /api/race-result — már nem csak számol: MENTI is az eredményt
  - .env fájl: az első valódi titok (adatbázis-jelszó) helye

Futtatás:  fastapi dev main.py   →   http://localhost:8000/docs
"""

import os

import httpx
import psycopg
from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from psycopg.rows import dict_row
from pydantic import BaseModel, Field

# ---- beállítások -----------------------------------------------------------

# A .env fájlból tölti be a környezeti változókat. A .env SOSEM kerül
# se GitHubra, se chatbe — ezért van a .gitignore-ban. A kódban csak a
# VÁLTOZÓ NEVE szerepel, az értéke a fájlban él, a te gépeden.
load_dotenv()

SB_URL = "https://tuudioczoyunmzyvhecu.supabase.co"          # publikus
SB_KEY = "sb_publishable_n0o2MS8uQXQ08ooEcIPF0w_5sGl0R7f"    # publikus

DB_URL = os.getenv("DATABASE_URL")
if not DB_URL:
    raise RuntimeError(
        "Hiányzik a DATABASE_URL. Hozd létre a .env fájlt a mappában "
        "(minta: .env.example), és tedd bele a Supabase kapcsolati címét."
    )

app = FastAPI(title="Vonatverseny API")
bearer = HTTPBearer()
http = httpx.AsyncClient(timeout=5)


def db():
    """Új adatbázis-kapcsolat. Kérésenként nyitunk egyet — ez azért nem
    pazarlás, mert a Supabase 'transaction pooler'-éhez csatlakozunk:
    az pontosan arra való, hogy a sok rövid kapcsolatot olcsóvá tegye."""
    return psycopg.connect(DB_URL)


# ---- kapuőr (változatlan a 2. változathoz képest) --------------------------

async def get_current_user(
    cred: HTTPAuthorizationCredentials = Depends(bearer),
) -> dict:
    valasz = await http.get(
        f"{SB_URL}/auth/v1/user",
        headers={
            "apikey": SB_KEY,
            "Authorization": f"Bearer {cred.credentials}",
        },
    )
    if valasz.status_code != 200:
        raise HTTPException(status_code=401, detail="Érvénytelen vagy lejárt belépési jegy.")
    adat = valasz.json()
    return {"id": adat["id"], "email": adat.get("email")}


# ---- végpontok --------------------------------------------------------------

ALAP_MENTES = {
    "level": 1, "coins": 0,
    "upgrades": {}, "paints": ["#C63B2C"], "paint": "#C63B2C",
}


@app.get("/api/health")
def health():
    return {"ok": True, "uzenet": "A szerver él!"}


@app.get("/api/me")
async def me(user: dict = Depends(get_current_user)):
    return user


@app.get("/api/save")
def get_save(user: dict = Depends(get_current_user)):
    """A játékos mentett állása — ha még nincs, az alapértékek.

    Figyeld meg a %s-t: az értéket SOHA nem fűzzük bele a SQL-szövegbe,
    hanem paraméterként adjuk át. Ez véd az SQL-injekció ellen — az
    adatbázis-világ XSS-e, ugyanaz az elv, mint az esc() a játékban.
    """
    with db() as conn, conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            "select level, coins, upgrades, paints, paint "
            "from saves where user_id = %s",
            (user["id"],),
        )
        sor = cur.fetchone()
    return sor or ALAP_MENTES


class RaceResult(BaseModel):
    level:  int   = Field(ge=1, le=200)
    won:    bool
    coins:  int   = Field(ge=0, le=60)
    stars:  int   = Field(ge=0, le=12)
    time_s: float = Field(gt=0, lt=600)


@app.post("/api/race-result")
def race_result(r: RaceResult, user: dict = Depends(get_current_user)):
    """Futameredmény: jutalomszámítás ÉS mentés, egy tranzakcióban.

    Új ellenőrzés: olyan szinten nem lehet nyerni, amit a mentésed
    szerint még ki sem nyitottál. A kliens azt MOND, amit akar — a
    szerver a SAJÁT adatához méri, nem a bemondáshoz.
    """
    jutalom = r.coins + 2 * r.stars + (25 + 5 * r.level if r.won else 0)
    uj_szint = r.level + 1 if r.won else r.level

    with db() as conn, conn.cursor(row_factory=dict_row) as cur:
        cur.execute("select level from saves where user_id = %s", (user["id"],))
        sor = cur.fetchone()
        ismert_szint = sor["level"] if sor else 1
        if r.level > ismert_szint:
            raise HTTPException(
                status_code=400,
                detail=f"A mentésed szerint a {ismert_szint}. szintnél tartasz — "
                       f"a(z) {r.level}. szint eredményét nem fogadhatom el.",
            )
        cur.execute(
            """
            insert into saves (user_id, level, coins)
            values (%(uid)s, %(lvl)s, %(jut)s)
            on conflict (user_id) do update set
              coins      = saves.coins + %(jut)s,
              level      = greatest(saves.level, %(lvl)s),
              updated_at = now()
            returning level, coins
            """,
            {"uid": user["id"], "lvl": uj_szint, "jut": jutalom},
        )
        friss = cur.fetchone()
        # a with-blokk végén a tranzakció magától véglegesedik (commit)

    return {"reward": jutalom, "level": friss["level"], "coins": friss["coins"]}
