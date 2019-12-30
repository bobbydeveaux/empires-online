# Design Document for Empires Online

## Entities

* Country
  * id
  * default_gold
  * default_bonds
  * default_territories
  * default_goods
  * default_people

* Player
  * id
  * username
  * password
  * email
  * email_verification_code
  * spawned_country_id

* Spawned_Country
  * id
  * country_id
  * game_id
  * gold
  * bonds
  * territories
  * goods
  * people
  * banks 

* Game
  * id
  * rounds
  * rounds_remaining
  * phase
  * creator_id
  * creation_date

Examples:

Country

|id|name|default_gold|default_bonds|default_territories|default_goods|default_people|
|---|-------|--------|-----|-----------------------|------------------|---|
| 4 | France | 5  | 1 | 4   | 2   | 3



Player

|id|username|password|email|email_verification|spawned-country-id|
|---|-------|--------|-----|-----------------------|------------------|
| 1 | Roger | 12345  | roger@gmail.com | abcdefg   | 1                |

Spawned Country

| id  | country_id  | game_id  | gold | bonds  | terrirtories | goods  | people  | banks  |
|---|---|---|---|---|---|---|---|---|
| 1  | 4  | 1  |  5 | 1  |  4 | 2  | 3  | 0  |

Game

|id|rounds|rounds_remaining|phase|creator_id|creation_date
|---|-------|--------|-----|-----------------------|------------------|
| 1 | 5 | 5  |  1 | 1 | 2019-12-30 22:17:10


## EndPoints


