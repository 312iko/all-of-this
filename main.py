"""ALL OF THIS game starts here. main.py is the entry point, it imports the main function from app.py which runs the game loop. Other modules are imported as needed for state management, narrative, puzzles, routing, etc."""
import subprocess
import sys

try:
    import pygame
except ImportError:
    print("pygame not found, installing dependencies...")
    try:
        subprocess.check_call(
            [sys.executable, "-m", "pip", "install", "-r", "requirements.txt"]
        )
        print("Installazione completata. Avvio del gioco...")
    except subprocess.CalledProcessError as e:
        print(f"Errore nell'installazione delle dipendenze: {e}")
        print("Installa manualmente con: pip install -r requirements.txt")
        sys.exit(1)

from game.app import main

if __name__ == "__main__":
    main()
