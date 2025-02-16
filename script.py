import os

# Définissez ici les extensions autorisées (fichiers texte ou code).
TEXT_EXTENSIONS = {
    ".txt", ".py", ".md", ".json", ".yaml", ".yml",
    ".html", ".xml", ".css", ".js", ".ts", ".java",
    ".c", ".cpp", ".h", ".hpp", ".sh", ".jsx"
}

# Liste des dossiers/fichiers à exclure automatiquement (sans demander).
EXCLUDED_FOLDERS = {"node_modules", "package", ".git", "package-lock.json", "package.json"}

def generer_nom_sortie(root_folder):
    """
    Génère le nom du fichier de sortie {Root}-Analyse.txt
    Si {Root}-Analyse.txt existe déjà, on ajoute +1, +2, etc.
    """
    base_name = os.path.basename(root_folder) + "-Analyse"
    extension = ".txt"
    
    candidate = base_name + extension
    index = 1
    while os.path.exists(os.path.join(root_folder, candidate)):
        candidate = f"{base_name}+{index}{extension}"
        index += 1
    
    return os.path.join(root_folder, candidate)

def demander_inclusion(path, is_dir):
    """
    Demande à l'utilisateur s'il veut inclure un dossier/fichier.
    
    - Pour un dossier : [o/n/a=all]
      - 'o' => inclure le dossier et on demandera pour ses sous-éléments
      - 'n' => on n’inclut pas le dossier
      - 'a' => on inclut TOUT le contenu du dossier (et sous-dossiers) d’un coup
    - Pour un fichier : [o/n]
      - 'o' => inclure
      - 'n' => ne pas inclure

    Renvoie :
      - True si l'utilisateur répond 'o'
      - False si l'utilisateur répond 'n'
      - "all" si l'utilisateur répond 'a' (uniquement valable si is_dir=True)
    """
    nom = os.path.basename(path)
    if is_dir:
        question = f"Voulez-vous inclure le dossier '{nom}' ? [o/n/a=all] : "
    else:
        question = f"Voulez-vous inclure le fichier '{nom}' ? [o/n] : "
    
    reponse = input(question).strip().lower()

    if reponse == "o":
        return True
    elif reponse == "n":
        return False
    elif reponse == "a" and is_dir:
        return "all"
    else:
        # Toute autre saisie => ne pas inclure
        return False

def est_cache(nom):
    """
    Détermine si un fichier ou un dossier est caché.
    On considère "caché" si le nom commence par un '.'
    """
    return nom.startswith('.')

def construire_arbo_interactive(current_path, arbo_dict, auto_include=False):
    """
    Parcours récursif du dossier/fichier `current_path`.

    Paramètres :
      - current_path (str) : le chemin complet de l'élément courant
      - arbo_dict (dict)   : dictionnaire dans lequel on stocke la structure
      - auto_include (bool): si True, on inclut automatiquement tout le contenu
                             sans reposer de questions (hérité d'un 'a' sur un dossier parent).

    arbo_dict renverra la structure sous la forme :
    {
      "type": "dir" ou "file",
      "name": <nom>,
      "path": <path_absolu>,
      "children": [...]  # seulement si "dir"
    }
    """
    nom = os.path.basename(current_path)

    # ------------------
    # 1) Gérer les exclusions et caches
    # ------------------
    # Si c'est un dossier ou un fichier à exclure, on ignore
    if nom in EXCLUDED_FOLDERS:
        return None

    # Ignorer s'il est caché (commence par '.')
    if est_cache(nom):
        return None

    # ------------------
    # 2) Si c'est un dossier
    # ------------------
    if os.path.isdir(current_path):
        # On demande ou on hérite de l'auto-include
        if not auto_include:
            reponse = demander_inclusion(current_path, is_dir=True)
            if reponse is False:
                # L'utilisateur a dit 'n'
                return None
            elif reponse == "all":
                # L'utilisateur a dit 'a'
                auto_include_current = True
            else:
                # L'utilisateur a dit 'o'
                auto_include_current = False
        else:
            # On hérite d'un 'a' du parent
            auto_include_current = True

        # On ajoute ce dossier à la structure
        arbo_dict["type"] = "dir"
        arbo_dict["name"] = nom
        arbo_dict["path"] = current_path
        arbo_dict["children"] = []
        
        # Lister le contenu
        try:
            contenu = sorted(os.listdir(current_path))
        except PermissionError:
            print(f"Permission refusée pour accéder à: {current_path}")
            return None
        
        # Pour chaque élément, on redescend récursivement
        for element in contenu:
            element_path = os.path.join(current_path, element)
            sub_dict = {}
            # On transmet auto_include_current pour les sous-éléments
            child = construire_arbo_interactive(element_path, sub_dict, auto_include=auto_include_current)
            if child is not None:
                arbo_dict["children"].append(child)
        
        return arbo_dict

    # ------------------
    # 3) Sinon, c'est un fichier
    # ------------------
    else:
        # Vérifier si c'est un fichier texte/code (via extension)
        _, extension = os.path.splitext(nom)
        if extension.lower() not in TEXT_EXTENSIONS:
            return None

        # Si on n'est pas en auto_include, on demande
        if not auto_include:
            inclure = demander_inclusion(current_path, is_dir=False)
            if not inclure:
                return None

        # On inclut ce fichier
        arbo_dict["type"] = "file"
        arbo_dict["name"] = nom
        arbo_dict["path"] = current_path
        return arbo_dict

def construire_sommaire(arbo_dict, prefix="", is_last=True, ancestors_last=[]):
    """
    Construit un sommaire textuel (sous forme de liste de lignes),
    en utilisant les caractères ASCII pour représenter un arbre :
    - ├─  et └─  pour les branches
    - │   pour la continuité

    Paramètres :
      - arbo_dict (dict)  : la structure d'un dossier ou fichier
      - prefix (str)      : le préfixe qui indique l'indentation
      - is_last (bool)    : indique si l'élément est le dernier dans son parent
      - ancestors_last (list[bool]) : pour savoir si les ancêtres sont derniers ou pas
    """
    lines = []
    if arbo_dict is None:
        return lines
    
    nom = arbo_dict["name"]
    node_type = arbo_dict["type"]  # "dir" ou "file"

    # Construire le préfixe d'arbre basé sur ancestors_last
    # (pour chaque ancêtre, si ce n'est pas le dernier on met "│   ", sinon on met "    ")
    tree_prefix = ""
    for is_ancestor_last in ancestors_last[:-1]:
        if not is_ancestor_last:
            tree_prefix += "│   "
        else:
            tree_prefix += "    "

    # Savoir si on utilise └─ ou ├─
    branch_symbol = "└─ " if is_last else "├─ "

    if node_type == "dir":
        lines.append(f"{tree_prefix}{branch_symbol}[D] {nom}")
        children = arbo_dict.get("children", [])
        for i, child in enumerate(children):
            child_is_last = (i == len(children) - 1)
            lines.extend(
                construire_sommaire(
                    child,
                    prefix="",  # (ce param n'est plus utilisé directement)
                    is_last=child_is_last,
                    ancestors_last=ancestors_last + [not child_is_last]
                )
            )
    else:
        # Fichier
        lines.append(f"{tree_prefix}{branch_symbol}[F] {nom}")
        # (Si un jour tu rajoutes l'extraction de fonctions, ce serait ici)
    
    return lines

def extraire_contenu_fichiers(arbo_dict, output_file, delimiter="="*60):
    """
    Parcourt la structure arbo_dict et écrit le contenu des fichiers
    dans output_file, avec des délimitations claires entre eux.
    """
    if arbo_dict is None:
        return
    
    if arbo_dict["type"] == "file":
        fichier_path = arbo_dict["path"]
        nom = arbo_dict["name"]
        # Écriture d'un en-tête
        output_file.write(f"\n{delimiter}\n")
        output_file.write(f"Fichier : {nom}\n")
        output_file.write(f"Chemin  : {fichier_path}\n")
        output_file.write(f"{delimiter}\n")
        
        # Lecture et écriture du contenu
        try:
            with open(fichier_path, "r", encoding="utf-8") as f:
                contenu = f.read()
            output_file.write(contenu)
        except Exception as e:
            # En cas d'erreur, on l'indique simplement
            output_file.write(f"\n[ERREUR LORS DE LA LECTURE : {e}]\n")
        
        output_file.write(f"\n{delimiter}\n\n")
    
    elif arbo_dict["type"] == "dir":
        # Parcourir récursivement les enfants
        for child in arbo_dict["children"]:
            extraire_contenu_fichiers(child, output_file, delimiter=delimiter)

def main():
    # Récupérer le dossier racine = dossier où est ce script.
    root_folder = os.path.dirname(os.path.abspath(__file__))

    # Construire l'arborescence (interaction + auto-include si 'a' choisi)
    root_dict = {}
    root_structure = construire_arbo_interactive(root_folder, root_dict, auto_include=False)
    
    if not root_structure:
        print("Aucun dossier/fichier n'a été sélectionné.")
        return
    
    # Générer le nom du fichier de sortie.
    output_path = generer_nom_sortie(root_folder)
    print(f"\nLe fichier de sortie sera : {output_path}\n")
    
    with open(output_path, "w", encoding="utf-8") as f_out:
        # 1) SOMMAIRE
        sommaire_lines = construire_sommaire(root_structure)
        f_out.write("SOMMAIRE DE L'ANALYSE\n")
        f_out.write("=====================\n")
        for line in sommaire_lines:
            f_out.write(line + "\n")
        
        # 2) CONTENU DES FICHIERS
        f_out.write("\n\nCONTENU DES FICHIERS\n")
        f_out.write("====================\n")
        
        extraire_contenu_fichiers(root_structure, f_out)
    
    print("Analyse terminée avec succès !")

if __name__ == "__main__":
    main()
