"""Shared site -> domain table (the asker chose the site). General sites (stackoverflow, cs, softwareengineering, superuser,
serverfault, unix, ...) have no entry; their questions get reference domains from tags only. Used by the pool builder and
by checks/human_anchor_checks.py check 3."""
SITE = {
 "security": "security-privacy", "crypto": "security-privacy", "reverseengineering": "security-privacy", "tor": "security-privacy",
 "dba": "data-engineering-databases", "networkengineering": "networking-distributed-communication",
 "quantumcomputing": "quantum-computing", "datascience": "artificial-intelligence-machine-learning",
 "ai": "artificial-intelligence-machine-learning", "genai": "artificial-intelligence-machine-learning",
 "devops": "devops-cloud-platform-engineering", "cstheory": "mathematical-theoretical-foundations",
 "langdev": "compilers-language-implementation", "computergraphics": "game-development-computer-graphics",
 "gamedev": "game-development-computer-graphics", "arduino": "embedded-iot-real-time-systems",
 "iot": "embedded-iot-real-time-systems", "raspberrypi": "embedded-iot-real-time-systems",
 "scicomp": "numerical-scientific-computing", "ux": "ux-design-hci", "pm": "software-process-documentation-collaboration",
 "sqa": "testing-quality-assurance", "android": "mobile-development",
 "bitcoin": "blockchain-distributed-ledger-technology", "ethereum": "blockchain-distributed-ledger-technology",
 "solana": "blockchain-distributed-ledger-technology", "cardano": "blockchain-distributed-ledger-technology",
 "monero": "blockchain-distributed-ledger-technology", "tezos": "blockchain-distributed-ledger-technology",
 "stellar": "blockchain-distributed-ledger-technology", "substrate": "blockchain-distributed-ledger-technology",
 "eosio": "blockchain-distributed-ledger-technology", "iota": "blockchain-distributed-ledger-technology",
 "or": "mathematical-theoretical-foundations", "proofassistants": "mathematical-theoretical-foundations",
 "stats": "mathematical-theoretical-foundations",
}
