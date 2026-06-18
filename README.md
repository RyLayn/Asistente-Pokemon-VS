# Pokémon Champions Assistant

**Asistente de combate Pokémon, de escritorio y sin conexión**, pensado para los
juegos actuales hasta **Leyendas Pokémon: Z-A** y **Pokémon Champions**.
Te ayuda a construir equipos, elegir tu selección frente al rival y tomar
decisiones durante la batalla: mejores ataques, cambios, megaevolución, marcador
de Pokémon debilitados y mucho más.

> Creado por **[RyLayn](https://github.com/RyLayn)** · © 2026 RyLayn

---

## ¿Qué es?

Una aplicación de escritorio (Windows) que funciona **100 % sin conexión** una
vez instalada: toda la Pokédex, los movimientos, las habilidades, los objetos y
los sprites viajan dentro de la aplicación. Está en **español**, con opción de
**Español (España)** o **Español (Latinoamérica)**.

La idea central es ser un **ayudante en el momento de la batalla**: cálculos de
efectividad correctos, recomendaciones claras y un marcador en vivo.

## Características

- **Constructor de equipos** con buscador predictivo. Al escribir un Pokémon
  aparece un **mini sprite** en las sugerencias para reconocerlo de un vistazo.
- **Dos modos**: Combate Individual y Combate Dobles (formato *Bring 6, Pick
  3/4*).
- **Selección frente al rival**: sugiere los mejores Pokémon a llevar según el
  equipo rival completo.
- **Pantalla de combate** con recomendaciones:
  - Tus **2 mejores ataques** contra el rival.
  - **Mejor cambio** y, en dobles, la **mejor pareja**.
  - **Ventajas, desventajas y velocidad** (quién ataca primero) y con qué tipos
    te golpea fuerte el rival.
  - **Cobertura** ofensiva y defensiva del equipo, con nombres concretos.
- **Megaevolución en pleno combate** (propias y del rival): actívala para
  recalcular con las características y tipos de la mega. Si equipas la **Piedra
  Mega** correcta, te avisa del **mejor momento** para megaevolucionar y recuerda
  la regla de **una megaevolución por equipo y combate**. Incluye las megas de
  **Leyendas Z-A** (que no usan piedra).
- **Marcador en vivo**: marca qué Pokémon han sido **debilitados** en cada
  bando, indica **quién derrotó a quién**, ve **cuántos quedan en pie** y consulta
  el registro. Los debilitados se excluyen automáticamente del análisis.
- **Importar / Exportar** equipos en formato Pokémon Showdown (pegando texto o
  desde archivo, con ida y vuelta).
- **Temas claro y oscuro** e insignias de tipo a color.

## Tecnologías

- **Python 3.11**
- **PySide6 (Qt 6)** para la interfaz de escritorio.
- **RapidFuzz** para la búsqueda predictiva tolerante a erratas.
- **orjson** (opcional) para lectura rápida de los datos.
- Datos de juego basados en **Pokémon Showdown** (roster, características, tipos,
  habilidades, movimientos y objetos, al día e incluyendo Z-A), con los
  **nombres en español** tomados de las cadenas de localización de PokeAPI.
- Empaquetado con **PyInstaller** para generar un ejecutable de Windows.

## Estructura del proyecto

```
PokemonChampionsAssistant/
├─ main.py                 Punto de entrada
├─ app/
│  ├─ config.py            Constantes (incluida la autoría)
│  ├─ core/                Motor de tipos, efectividad y análisis de combate
│  ├─ models/              Modelos de datos (Pokémon, movimiento, equipo…)
│  ├─ services/            Base de datos, búsqueda, sprites, equipos, estado
│  ├─ import_export/       Formato Showdown e E/S de equipos
│  ├─ ui/                  Ventana principal, widgets y temas (.qss)
│  └─ data/                Base de datos local (JSON) y sprites
├─ tests/                  Pruebas (pytest)
├─ assets/                 Iconos
├─ requirements.txt
├─ LICENSE                 MIT © 2026 RyLayn
└─ README.md
```

## Cómo ejecutarlo (desde el código)

Requisitos: Python 3.11+.

```bash
pip install -r requirements.txt
python main.py
```

La aplicación guarda tus ajustes y equipos en la carpeta de datos del usuario
del sistema (en Windows, dentro de `%LOCALAPPDATA%\PokemonChampionsAssistant`),
por lo que el ejecutable no crea carpetas de datos a su lado.

## Cómo se calcula (y por qué es fiable)

La tabla de tipos y los datos de combate están **validados contra Pokémon
Showdown**: las 324 interacciones de tipo coinciden, así como las potencias y
categorías de los movimientos. La efectividad usa STAB (1,5×) y los
multiplicadores estándar, y las recomendaciones se basan en la relación entre el
poder ofensivo y la resistencia defensiva de cada enfrentamiento.

## Cómo actualizar o ampliar los datos

Toda la información vive en archivos JSON dentro de `app/data/database/seed/` y
se aplica al iniciar la aplicación. No necesitas tocar el código para mantenerla
al día:

- `locale_latam.json` — equivalencias **Español (España) → Español (Latino)**.
  Añade pares para traducir más nombres.
- `fixes_es.json` — **correcciones y renombramientos** (por ejemplo, cambios de
  nombre de Gen 9 / Z-A como *Foco Resplandor → Cañón Resplandor* o *Foco Interno
  → Fuerza Mental*), y altas de movimientos que la fuente no tradujo.
- `mega_evolution.json` — relación de **megaevoluciones** (especie, forma y, si
  procede, su Piedra Mega).

Para cualquiera de ellos: edita el JSON, guarda y reinicia la aplicación. Si en
el futuro quieres reconstruir toda la base desde cero, los datos de juego
provienen de Pokémon Showdown y los nombres en español de las cadenas de
localización; basta con regenerar esos JSON con esas fuentes.

## Qué puedes modificar

Eres libre de **usar, modificar y ampliar** este proyecto (nuevas funciones,
datos, traducciones, temas, etc.), con una única condición:

> **Conserva la atribución al autor original, RyLayn
> (https://github.com/RyLayn), en el código, en la ventana «Acerca de» y en este
> README.** No elimines ni ocultes el crédito para atribuirte la autoría
> original del proyecto.

## Licencia

Distribuido bajo licencia **MIT** (ver [`LICENSE`](LICENSE)). La licencia exige
mantener el aviso de copyright y la atribución a **RyLayn** en todas las copias o
partes sustanciales del software.

---

Hecho con cariño por **[RyLayn](https://github.com/RyLayn)** · © 2026 RyLayn
