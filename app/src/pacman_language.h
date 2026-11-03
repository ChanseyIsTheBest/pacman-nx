// pacman-nx (2026-11-03, from nights-nx and sa2-nx): pacman.toml "language" (auto, english, japanese, french, german,
// spanish, italian, schinese, tchinese) as the Xbox language the game reads (user_language).
#pragma once

namespace pacman::language {

// Once the config is loaded, before the game starts.
void Apply();

}  // namespace pacman::language
