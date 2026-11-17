"""Point d'entrée minimal du projet ytloop.

Ajoutez ici la logique du bot lorsque sa plateforme et son comportement seront définis.
"""

import logging


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)


def main() -> None:
    logging.info("ytloop démarre.")
    logging.info("Aucune logique métier n'est configurée pour le moment.")


if __name__ == "__main__":
    main()
