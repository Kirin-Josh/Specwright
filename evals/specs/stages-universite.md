# Gestion des demandes de stage — Cahier des charges

Version 1.0 · Département d'informatique · Spécification fictive écrite pour les évaluations de Specwright

## 1. Contexte

Le département accueille environ 300 étudiants de master chaque année, qui effectuent tous un
stage en entreprise. Actuellement, les étudiants déposent leur convention de stage en version
papier au secrétariat, qui saisit ensuite chaque convention dans un tableur. Les dossiers
incomplets sont fréquents et les relances se font par téléphone.

Le présent document décrit une application web qui remplace ce circuit papier.

### 1.1 Acteurs

| Acteur | Rôle |
|---|---|
| Étudiant | Dépose et suit sa demande de stage |
| Enseignant référent | Valide le sujet du stage sur le plan pédagogique |
| Secrétariat | Vérifie les pièces et gère les conventions |
| Tuteur en entreprise | Évalue le stagiaire en fin de stage |

## 2. Exigences fonctionnelles

| ID | Exigence |
|---|---|
| EF-01 | L'étudiant crée une demande de stage en indiquant l'entreprise, le sujet, les dates de début et de fin et le tuteur en entreprise. La durée doit être comprise entre 8 et 24 semaines. |
| EF-02 | L'étudiant joint la convention signée au format PDF, d'une taille maximale de 10 Mo. |
| EF-03 | L'enseignant référent valide ou refuse le sujet ; un commentaire est obligatoire en cas de refus. |
| EF-04 | Après la validation pédagogique, le secrétariat vérifie les pièces et passe la demande au statut « Convention signée ». |
| EF-05 | L'étudiant, son référent et le secrétariat reçoivent un courriel à chaque changement de statut de la demande. |
| EF-06 | Le tuteur en entreprise remplit en ligne la fiche d'évaluation de fin de stage grâce à un lien personnel valable 30 jours, sans créer de compte. |
| EF-07 | Le secrétariat exporte la liste des stages de l'année universitaire au format Excel (.xlsx). |

## 3. Exigences de sécurité

- **ES-01** — Les utilisateurs s'authentifient avec le CAS de l'université ; l'application ne gère aucun mot de passe local.
- **ES-02** — Un étudiant ne voit que ses propres demandes ; un enseignant ne voit que les demandes dont il est le référent.
- **ES-03** — Les conventions sont conservées cinq ans, puis supprimées automatiquement.

## 4. Exigences techniques

- **ET-01** — L'application fonctionne sur les navigateurs récents, y compris sur téléphone.
- **ET-02** — Les données sont hébergées sur les serveurs de l'université, dans une base PostgreSQL.

## 5. Autres contraintes

L'interface doit être disponible en français et en anglais ; chaque utilisateur choisit sa
langue. Le département prévoit une mise en service pour la rentrée de septembre.

## 6. Critères d'acceptation

- **CA-01** — Une demande de 6 semaines est refusée dès la saisie, avec un message qui rappelle la durée minimale. (Couvre : EF-01.)
- **CA-02** — Une demande suit tout le parcours, de sa création jusqu'au statut « Convention signée », et chaque acteur reçoit les courriels attendus. (Couvre : EF-01 à EF-05.)
- **CA-03** — Un tuteur qui ouvre le lien d'évaluation au bout de 31 jours voit un message indiquant que le lien a expiré. (Couvre : EF-06.)
- **CA-04** — Un étudiant qui remplace l'identifiant d'une demande dans l'adresse par celui d'un autre étudiant reçoit une erreur d'accès refusé. (Couvre : ES-02.)

## 7. Hors périmètre

- La signature électronique des conventions n'est pas demandée : les conventions restent signées sur papier puis numérisées.
- La gestion des gratifications versées aux stagiaires est hors périmètre.
- Aucune application mobile native n'est prévue.

## 8. Glossaire

- **Référent** — enseignant qui suit l'étudiant pendant son stage.
- **Convention** — contrat tripartite entre l'étudiant, l'université et l'entreprise.
