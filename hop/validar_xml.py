from pathlib import Path
import xml.etree.ElementTree as ET
root=Path(__file__).resolve().parent
arquivos=list((root/"pipelines").glob("*.hpl"))+list((root/"workflows").glob("*.hwf"))
erros=0
for arq in arquivos:
    try:
        ET.parse(arq); print("OK ", arq.relative_to(root))
    except Exception as exc:
        erros+=1; print("ERRO", arq.relative_to(root), exc)
raise SystemExit(1 if erros else 0)
