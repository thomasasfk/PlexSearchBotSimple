# Plex Search Search Bot Simple [![Tests](https://github.com/thomasasfk/PlexSearchBotSimple/actions/workflows/python-tests.yml/badge.svg)](https://github.com/thomasasfk/PlexSearchBotSimple/actions/workflows/python-tests.yml)

A Telegram bot that searches Jackett indexers and uploads to rTorrent. Despite the repository name, this has no Plex integration.

## Commands

| Command | Description | Example |
|---------|-------------|---------|
| `/search [term]` | Search for content | `/search arcane` |
| `/get[id]` | Download from a search result | `/get14492` |
| `/download [magnet]` | Download using magnet link | `/download magnet:?xt=...` |

## This branch holds my personal simpler version