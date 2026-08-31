# V-RyLune

Your Ryzom inventories and guild chests, outside the game.

Browse your Ryzom character inventories and your guild chests outside the game,
using the official web API.

## What it shows

* Bags, apartments, mounts, mektoubs, zigs and guild chests, with each item's
  readable name, quality, stack size and bulk.
* A movement log: what went in and out of a chest since you last looked. The
  API keeps no history, so the app is the only witness.
* A character's skill tree, with progress through the current level and the
  branches that are fully trained.
* Outposts held across Atys, who holds what, and a log of takes and losses.
* Atys weather as a chart, with the season's supreme and excellent materials.

## Getting started

You need an API key, created on the Ryzom website under "My applications". A key
grants read access to the inventories it covers: treat it like a password. The
app asks for nothing else, creates no account, and sends your data nowhere —
everything stays on the phone.

Readable item names come from the *string_client.pack* file of your Ryzom
installation, imported once from the menu. Without it, the app shows sheet
identifiers.

## Origin

V-RyLune is the Android port of Misugi's zyRoom, written in Delphi for Windows.
It is a derivative work, under the same licence — GNU AGPLv3.

V-RyLune is not affiliated with Winch Gate, the publisher of Ryzom.
