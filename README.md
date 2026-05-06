# Guide d'utilisation — Détection vidéo SAM3

Ce guide explique comment lancer des analyses de détection d'objets sur des vidéos, **sans avoir besoin de connaître Python ou la programmation**. Suivez les étapes dans l'ordre.

---

## Sommaire

1. [Ce que fait l'outil](#ce-que-fait-loutil)
2. [Étape 1 — Ouvrir WSL](#étape-1--ouvrir-wsl)
3. [Étape 2 — Activer l'environnement](#étape-2--activer-lenvironnement)
4. [Étape 3 — Se connecter à Hugging Face (première fois uniquement)](#étape-3--se-connecter-à-hugging-face-première-fois-uniquement)
5. [Étape 4 — Lancer une analyse](#étape-4--lancer-une-analyse)
6. [Paramètres expliqués](#paramètres-expliqués)
7. [Analyser un dossier entier](#analyser-un-dossier-entier)
8. [Fichiers de sortie](#fichiers-de-sortie)
9. [Problèmes fréquents](#problèmes-fréquents)

---

## Ce que fait l'outil

Le script analyse une ou plusieurs vidéos et **détecte automatiquement les objets** que vous lui décrivez en texte (ex : `"bee"`, `"flower"`, `"insect"`).

Pour chaque frame analysée, il génère :
- une **image** montrant l'objet détecté (pixels originaux sur fond noir)
- un **fichier JSON** récapitulatif avec le nombre d'objets, les scores de confiance, etc.

---

## Étape 1 — Ouvrir WSL

WSL est un terminal Linux intégré à Windows. C'est depuis là que les analyses sont lancées.

**Option A — Via VSCode**

1. Ouvrir le dossier du projet dans VSCode
2. Ouvrir un terminal intégré : menu **Terminal → New Terminal** (ou raccourci `` Ctrl+` ``)
3. Dans le terminal, taper `wsl` et appuyer sur Entrée

**Option B — Via Git Bash**

1. Ouvrir Git Bash (clic droit sur le bureau → *Git Bash Here*, ou via le menu Démarrer)
2. Taper `wsl` et appuyer sur Entrée

Dans tous les cas, vous devriez voir quelque chose comme :
```
paulf@24-310:/mnt/c/...
```

---

## Étape 2 — Activer l'environnement

Avant chaque session, il faut activer l'environnement sam3. Taper exactement :

```bash
conda activate sam3
```

Le début de la ligne doit changer de `(base)` à `(sam3)` :
```
(sam3) paulf@24-310:~$
```

> Si vous voyez `(sam3)` au début, l'environnement est bien actif.

---

## Étape 3 — Se connecter à Hugging Face (première fois uniquement)

Cette étape est à faire **une seule fois**. Elle permet de télécharger le modèle SAM3 depuis Hugging Face.

Le token se trouve dans le fichier `.env` à la racine du projet (`stage_evs/.env`), à la ligne `HUGGINGFACE_TOKEN=...`.

```bash
hf auth login --token <coller le token ici>
```

> Une fois connecté, le token est sauvegardé localement. Vous n'aurez plus besoin de relancer cette commande lors des prochaines sessions.

---

## Étape 4 — Lancer une analyse

### Sur une seule vidéo

```bash
python /mnt/c/Users/jeanne.cayre/Documents/stage_evs/sam3/scripts/custom/detect-video.py \
  --prompt "bee" \
  --input "/mnt/c/chemin/vers/mavideo.MP4" \
  --out-dir /mnt/c/Users/jeanne.cayre/Documents/stage_evs/sam3/out/videos/mon_analyse \
  --step 30
```

**Exemple concret** avec la caméra 1, vidéo 04230066 :

```bash
python /mnt/c/Users/jeanne.cayre/Documents/stage_evs/sam3/scripts/custom/detect-video.py \
  --prompt "bee" \
  --input "/mnt/c/Users/jeanne.cayre/Documents/paulf/bees/Videos Dardilly 2/Cam 1/100EK113/04230066.MP4" \
  --out-dir /mnt/c/Users/jeanne.cayre/Documents/stage_evs/sam3/out/videos/test1 \
  --step 30
```

> Les chemins Windows `C:\Dossier\Fichier` s'écrivent en WSL `/mnt/c/Dossier/Fichier` (antislashes `\` remplacés par des slashes `/`, et `C:` devient `/mnt/c`).

---

## Paramètres expliqués

| Paramètre | Rôle | Exemple |
|-----------|------|---------|
| `--prompt` | Ce qu'on cherche dans la vidéo, en anglais | `"bee"`, `"flower"`, `"insect"` |
| `--input` | Chemin vers la vidéo à analyser | `"/mnt/c/.../mavideo.MP4"` |
| `--out-dir` | Dossier où seront sauvegardés les résultats | `/mnt/c/.../sam3/out/videos/test1` |
| `--step` | 1 frame analysée toutes les N frames | `30` = 1 frame/s pour une vidéo 30fps |

### Choisir le bon `--step`

Le step détermine combien de frames de la vidéo sont analysées :

| Framerate vidéo | Step | Fréquence d'analyse |
|-----------------|------|---------------------|
| 30 fps | 30 | 1 frame par seconde |
| 30 fps | 15 | 2 frames par seconde |
| 30 fps | 60 | 1 frame toutes les 2 secondes |
| 30 fps | 1 | toutes les frames (très lent) |

> Un step plus petit = plus de précision mais plus lent. Un step de 30 est un bon compromis pour commencer.

---

## Analyser un dossier entier

### Toutes les vidéos d'un dossier (sans sous-dossiers)

```bash
python /mnt/c/Users/jeanne.cayre/Documents/stage_evs/sam3/scripts/custom/detect-video.py \
  --prompt "bee" \
  --input-dir "/mnt/c/Users/jeanne.cayre/Documents/paulf/bees/Videos Dardilly 2/Cam 1/100EK113" \
  --out-dir /mnt/c/Users/jeanne.cayre/Documents/stage_evs/sam3/out/videos/batch1 \
  --step 30
```

### Toutes les vidéos d'un dossier ET ses sous-dossiers (récursif)

Ajouter `--recursive` à la fin :

```bash
python /mnt/c/Users/jeanne.cayre/Documents/stage_evs/sam3/scripts/custom/detect-video.py \
  --prompt "bee" \
  --input-dir "/mnt/c/Users/jeanne.cayre/Documents/paulf/bees/Videos Dardilly 2" \
  --out-dir /mnt/c/Users/jeanne.cayre/Documents/stage_evs/sam3/out/videos/batch_all \
  --step 30 \
  --recursive
```

> **Attention :** si le dossier de sortie (`--out-dir`) existe déjà et contient des fichiers, il sera **entièrement supprimé et recréé** au lancement. Pensez à changer le nom du dossier de sortie pour chaque nouvelle analyse.

---

## Fichiers de sortie

### Analyse d'une seule vidéo

```
out/videos/mon_analyse/
  04230066_mask_bee_frame0000_obj0.png   ← objet détecté frame 0
  04230066_mask_bee_frame0030_obj0.png   ← objet détecté frame 30
  ...
  summary.json                           ← récapitulatif complet
```

### Analyse d'un dossier (batch)

```
out/videos/batch1/
  batch_summary.json                     ← récapitulatif global de toutes les vidéos
  04230066/
    04230066_mask_bee_frame0000_obj0.png
    summary.json
  04230067/
    ...
```

### Contenu du `summary.json` (par vidéo)

```json
{
  "video": "04230066.MP4",
  "prompt": "bee",
  "video_fps": 29.97,
  "video_duration_s": 60.07,
  "step": 30,
  "effective_fps": 1.0,
  "total_frames_processed": 61,
  "frames_with_detections": 12,
  "total_mask_images": 15,
  "tracked_objects_count": 2,
  "tracked_obj_ids": [0, 1],
  "frames": [ ... ]
}
```

| Champ | Signification |
|-------|---------------|
| `video_fps` | Framerate de la vidéo originale |
| `video_duration_s` | Durée de la vidéo en secondes |
| `effective_fps` | Fréquence réelle d'analyse (fps / step) |
| `total_frames_processed` | Nombre de frames passées dans le modèle |
| `frames_with_detections` | Frames où au moins un objet a été trouvé |
| `total_mask_images` | Nombre d'images de masque générées |
| `tracked_objects_count` | Nombre d'objets distincts trackés sur la vidéo |

> `tracked_obj_ids` : SAM3 assigne un identifiant stable à chaque objet tracké. L'objet `obj_id=0` est le même objet suivi d'une frame à l'autre — ce n'est pas une détection indépendante par frame.

---

## Problèmes fréquents

### `conda: command not found`
L'environnement conda n'est pas initialisé dans WSL. Taper :
```bash
source ~/miniconda3/etc/profile.d/conda.sh
conda activate sam3
```

### `(base)` au lieu de `(sam3)` au début de la ligne
L'environnement n'est pas activé. Taper :
```bash
conda activate sam3
```

### `Input not found: ...`
Le chemin vers la vidéo est incorrect. Vérifier :
- que les antislashes `\` sont bien remplacés par des slashes `/`
- que `C:` est bien remplacé par `/mnt/c`
- que le nom du fichier est exact (attention aux majuscules : `.MP4` ≠ `.mp4`)

### `No video files found in ...`
Le dossier `--input-dir` ne contient pas de fichiers vidéo reconnus (`.mp4`, `.mov`, `.avi`, `.mkv`). Vérifier le chemin du dossier.

### La fenêtre WSL se ferme toute seule
Ne pas fermer la fenêtre pendant l'analyse. Le traitement peut prendre plusieurs minutes par vidéo.

---

## Formats vidéo acceptés

`.mp4` `.mov` `.avi` `.mkv`

---

## Analyse d'images — `detect-image.py`

Le script `detect-image.py` fonctionne exactement de la même façon que `detect-video.py`, mais sur des **images fixes** plutôt que des vidéos.

Les étapes sont identiques : ouvrir WSL (Étape 1), activer l'environnement `sam3` (Étape 2), puis lancer le script en remplaçant simplement `detect-video.py` par `detect-image.py` et en adaptant le chemin d'entrée vers une image.

```bash
python /mnt/c/Users/jeanne.cayre/Documents/stage_evs/sam3/scripts/custom/detect-image.py \
  --prompt "bee" \
  --input "/mnt/c/chemin/vers/monimage.jpg" \
  --out-dir /mnt/c/Users/jeanne.cayre/Documents/stage_evs/sam3/out/images/mon_analyse
```

Les paramètres `--prompt`, `--input`, `--input-dir`, `--out-dir` et `--recursive` fonctionnent de la même manière. Le paramètre `--step` n'existe pas pour les images (il n'y a qu'une seule frame à analyser).

### Formats image acceptés

`.jpg` `.jpeg` `.png` `.bmp` `.tiff`

