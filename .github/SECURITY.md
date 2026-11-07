# Política de seguridad

## Versiones con soporte

Solo la última versión publicada en [PyPI](https://pypi.org/project/colombia-open/)
y el último bundle de datos en
[GitHub Releases](https://github.com/davidcasr/colombia-open/releases)
reciben correcciones de seguridad.

## Cómo reportar una vulnerabilidad

**No abras un issue público.** Usa el reporte privado de GitHub:

1. Ve a la pestaña **Security** del repositorio.
2. Haz clic en **Report a vulnerability**.
3. Describe el problema, cómo reproducirlo y su posible impacto.

Recibirás una primera respuesta en un plazo de **7 días**. Si el reporte se
confirma, coordinaremos contigo la corrección y la fecha de divulgación, y te
daremos crédito en el aviso (salvo que prefieras quedar en el anonimato).

## Qué cuenta como vulnerabilidad aquí

- Código en `colombia_open/` que ejecute código arbitrario, lea/escriba fuera
  del directorio de caché, o acepte un bundle de datos sin verificar su SHA256
  (`data_manager.py`).
- Problemas en el servidor MCP (`colombia_open/mcp_server.py`) que permitan
  acceder a archivos o recursos fuera de los datasets publicados.
- Workflows de GitHub Actions que expongan secretos o permitan que una PR
  externa escriba en el repositorio o publique a PyPI.
- Datos personales sensibles publicados por error dentro de un dataset.

## Qué NO es una vulnerabilidad

- Un dato incorrecto o desactualizado de una fuente oficial → abre un issue
  de tipo **Bug en un dataset**.
- Una fuente caída o un extractor en `source_mode="fallback"` → issue normal.
