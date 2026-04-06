# Auto Patch System with GitHub Releases

Ce projet met en place un système de **mise à jour différentielle automatique** basé sur GitHub Releases et GitHub Actions.

## Fonctionnement

À chaque release :
- Un fichier `release-full.zip` est upload
- Une GitHub Action se déclenche
- Elle compare avec la release précédente
- Génère un patch
- Upload le patch automatiquement

## Structure

Release :
- `release-full.zip`
- `patch-vX-to-vY.zip`

Patch :
- `files/` → fichiers ajoutés/modifiés
- `manifest.json` → fichiers supprimés

## Cas particulier

Si seulement des fichiers sont supprimés :
- `files/` peut être vide
- uniquement `manifest.json`

## Workflow

Déclenché sur :
```
on:
  release:
    types: [published]
  workflow_dispatch:
```

Étapes :
1. Download current release
2. Download previous release
3. Compare
4. Generate patch
5. Upload patch

## Script

`.github/scripts/generate_patch.py`

- Compare les fichiers via hash
- Détecte ajout / modification / suppression
- Génère patch zip

## Utilisation

1. Télécharger patch
2. Copier `files/`
3. Supprimer fichiers listés dans manifest

## Important

- Nom obligatoire : `release-full.zip`
- Pas de build dans l'action
- Structure stable recommandée

## Limitations

- Gros fichiers = re-download complet
- Pas de delta binaire

## Avantages

- Léger
- Automatique
- Simple
- Pas de double build
