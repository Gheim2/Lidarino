import subprocess
import sys
import os

# --- CONFIGURAZIONE WINDOWS ---
# Su Windows colcon genera file .bat, non .bash
WORKSPACE_SETUP = r"install\setup.bat"

def run_command(command, needs_sourcing=False):
    """Esegue un comando in CMD. Se needs_sourcing è True, fa prima il call del workspace."""
    
    if needs_sourcing and os.path.exists(WORKSPACE_SETUP):
        # Su Windows usiamo cmd /c e call per concatenare i comandi
        full_command = f'cmd /c "call {WORKSPACE_SETUP} && {command}"'
    elif needs_sourcing:
        print(f"\n[Avviso] File {WORKSPACE_SETUP} non trovato. Esegui prima la build (Opzione 1).")
        full_command = command
    else:
        full_command = command

    print(f"\n[Esecuzione] {full_command}\n" + "-"*50)
    
    try:
        subprocess.run(full_command, shell=True, check=True)
    except subprocess.CalledProcessError as e:
        print(f"\n[Errore] Il comando ha fallito con codice: {e.returncode}")
    except KeyboardInterrupt:
        print("\n[Interrotto] Esecuzione fermata dall'utente (Ctrl+C).")
    
    print("-" * 50 + "\n")

def main():
    while True:
        print("=== Lidarino ROS 2 Manager (Windows / Pixi Edition) ===")
        print("1. 🏗️\tColcon Build (compila tutto il workspace)")
        print("2. 🌍\tAvvia Isaac Sim Bridge (sim_isaac.launch.py)")
        print("3. 👁️\tAvvia Rviz2 (Standalone)")
        print("4. 🖥️\tVisualizza Lidarino in Rviz2 [Solo display]")
        print("5. 🎮\tControlla Lidarino con Tastiera (Teleop)")
        print("6. 🤖\tAvvia Esplorazione Autonoma (Explore Lite)")
        print("0. ❌\tEsci")
        
        scelta = input("\nSeleziona un'opzione: ")

        if scelta == '1':
            run_command("colcon build --symlink-install")
            
        elif scelta == '2':
            print("\n[Avvio] Lancio nodi per Isaac Sim (TF, Navigation, SLAM)...")
            run_command("ros2 launch lidarino_bringup sim_isaac.launch.py", needs_sourcing=True)
            
        elif scelta == '3':
            run_command("rviz2 --ros-args -p use_sim_time:=true", needs_sourcing=True)

        elif scelta == '4':
            print("\n[Avvio] Lancio il display di Lidarino...")
            run_command("ros2 launch lidarino_description display.launch.py variant:=isaac", needs_sourcing=True)

        elif scelta == '5':
            print("\n[Avvio] Lancio il controller tramite tastiera...")
            # Semplificato per usare il cmd_vel standard
            run_command("ros2 run teleop_twist_keyboard teleop_twist_keyboard --ros-args -p stamped:=true -p frame_id:=base_link", needs_sourcing=True)

        elif scelta == '6':
            print("\n[Avvio] L'esplorazione autonoma...")
            # Modificato il path per essere relativo e compatibile con Windows
            run_command(r"ros2 run explore_lite explore --ros-args --params-file src\lidarino_description\config\explore.yaml", needs_sourcing=True)

        elif scelta == '0':
            print("Uscita dal manager.")
            sys.exit(0)
            
        else:
            print("Opzione non valida, riprova.")

if __name__ == "__main__":
    main()