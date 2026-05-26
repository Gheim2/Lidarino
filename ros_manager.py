import subprocess
import sys
import os

# --- CONFIGURAZIONE ---
# Modifica questo percorso se il tuo file setup.bash si trova altrove
WORKSPACE_SETUP = "install/setup.bash"

def run_command(command, needs_sourcing=False):
    """Esegue un comando nel terminale. Se needs_sourcing è True, fa prima il source del workspace."""
    
    if needs_sourcing and os.path.exists(WORKSPACE_SETUP):
        # Concatena il comando di source con il comando desiderato
        full_command = f"bash -c 'source /opt/ros/jazzy/setup.bash && source {WORKSPACE_SETUP} && {command}'"
    elif needs_sourcing:
        print(f"\n[Avviso] File {WORKSPACE_SETUP} non trovato. Eseguo solo il source di ROS base.")
        full_command = f"bash -c 'source /opt/ros/jazzy/setup.bash && {command}'"
    else:
        full_command = command

    print(f"\n[Esecuzione] {full_command}\n" + "-"*50)
    
    try:
        # Esegue il comando. check=True alza un'eccezione se il comando fallisce
        subprocess.run(full_command, shell=True, check=True)
    except subprocess.CalledProcessError as e:
        print(f"\n[Errore] Il comando ha fallito con codice: {e.returncode}")
    except KeyboardInterrupt:
        print("\n[Interrotto] Esecuzione fermata dall'utente (Ctrl+C).")
    
    print("-" * 50 + "\n")

def main():
    while True:
        print("=== Lidarino ROS 2 Manager ===")
        print("1. 🛠️  Compila Xacro in URDF (Solo per test manuali)")
        print("2. 🏗️  Colcon Build (compila tutto il workspace)")
        print("3. 🌍 Avvia Gazebo (Controller Lidarino)")
        print("4. 👁️  Avvia Rviz2 (Vuoto)")
        print("5. 🚀 Avvia Lidarino in Rviz (Launch File Completo)")
        print("0. ❌ Esci")
        
        scelta = input("\nSeleziona un'opzione: ")

        if scelta == '1':
            in_file = input("Percorso file Xacro [default: src/lidarino_description/urdf/Lidarino.urdf.xacro]: ") or "src/lidarino_description/urdf/Lidarino.urdf.xacro"
            out_file = input("Percorso output URDF [default: src/lidarino_description/urdf/Lidarino.urdf]: ") or "src/lidarino_description/urdf/Lidarino.urdf"
            run_command(f"xacro {in_file} > {out_file}", needs_sourcing=True)
            
        elif scelta == '2':
            run_command("colcon build --symlink-install")
            run_command("source install/setup.bash", needs_sourcing=False) 
            
        elif scelta == '3':
            print("\n[Avvio] Lancio Gazebo e il controller del Lidarino...")
            run_command("ros2 launch lidarino_description gazebo.launch.py", needs_sourcing=True)
            
        elif scelta == '4':
            run_command("rviz2 --ros-args -p use_sim_time:=true", needs_sourcing=True)

        elif scelta == '5':
            print("\n[Avvio] Lancio l'ecosistema di Lidarino (Rviz + TF)...")
            # Un solo comando elegante per far partire tutto!
            run_command("ros2 launch lidarino_description display.launch.py", needs_sourcing=True)
            
        elif scelta == '0':
            print("Uscita dal manager.")
            sys.exit(0)
            
        else:
            print("Opzione non valida, riprova.")

if __name__ == "__main__":
    main()