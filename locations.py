import json

MAP_LOCATIONS = {
    "lagos":{
        "island":[
            {
            "location":"lekki",
            "contact":"09085199354",
            "name":"Seunfunmi Okuntola"
            }
        ],
        "mainland":[
            {
                "location":"Ikeja/Maryland",
                "contact":"08186104998",
                "name":"Tola Daini"
            },
            {
                "location":"Isolo/Ajao Estate",
                "contact":"08099448709",
                "name":"Seun Odegbami"
            },
            {
                "location":"Surulere",
                "contact":"08082958491\n08092400769",
                "name":"Pascal Ekeh"
            },
            {
                "location":"Berger/Omole Phase 1",
                "contact":"08158376282",
                "name":"Onome Agesse"
            },
            {
                "location":"Gbagada",
                "contact":"08037442973",
                "name":"Demilade Olafisoye"
            },
            {
                "location":"Egbeda/Igando",
                "contact":"08138388007",
                "name":"Witness Usoro"
            },
            {
                "location":"Ogudu",
                "contact":"08166117441\n08148300299",
                "name":"Zion Rotimi"

            },
            {
                "location":"Ogba",
                "contact":"08189024964",
                "name":"Funom Yakubu"
            },
            {
                "location":"Agege",
                "contact":"08162973646",
                "name":"Bukola Alatishe"
            },
            {
                "location":"Yaba",
                "contact":"07067998749",
                "name":"Chide Isaac"
            },
            {
                "location":"Ikotun",
                "contact":"09032141975",
                "name":"Dolapo Richards"
            },
            {
                "location":"Magodo/Ketu",
                "contact":"08115557080",
                "name":"Muyiwa Ogunmade"
            }
        ]
    },
    "abuja":{
        "amac":[
            {
                "location":"lugbe",
                "contact":"08143140914",
                "name":"Ajifa Ali"
            },
            {
                "location":"lugbe",
                "contact":"08164660697",
                "name":"Philip Somiari"
            },
            {
                "location":"lokogoma",
                "contact":"08081822074",
                "name":"Goodness"
            },
            {
                "location":"lokogoma",
                "contact":"07030936430",
                "name":"Anselm"
            },
            {
                "location":"Gudu/Apo Legislative Quaters",
                "contact":"07035294089",
                "name":"Damilola"
            },
            {
                "location":"maitama/gishiri",
                "contact":"07062651122",
                "name":"Emaediong"
            },
            {
                "location":"maitama/gishiri",
                "contact":"08130475372",
                "name":"Imaobong"
            },
            {
                "location":"garki",
                "contact":"08179335521",
                "name":"Chinedu"
            },
            {
                "location":"Wuse",
                "contact":"08024266962",
                "name":"Ukeme"
            },
            {
                "location":"Lifecamp/Kado/Jabi",
                "contact":"08077195219",
                "name":"Chito Nwigene"
            },
            {
                "location":"wuye/utako",
                "contact":"08020579122",
                "name":"Paul Usikpo"
            },
            {
                "location":"wuye/utako",
                "contact":"08069839038",
                "name":"Edozie"
            },
            {
                "location":"gwarinpa/dawaki",
                "contact":"08052464065",
                "name":"Joan Onotu"
            },
            {
                "location":"gwarinpa/dawaki",
                "contact":"08138533068",
                "name":"Kemi"
            },
            {
                "location":"nyanya/Maraba",
                "contact":"07066700121",
                "name":"Lydia Uwota"
            },
            {
                "location":"nyanya/Maraba",
                "contact":"08133464118",
                "name":"Chioba"
            },
            {
                "location":"kubwa/Dei-dei",
                "contact":"07066813520",
                "name":"Opeyemi"
            },
            {
                "location":"kubwa/Dei-dei",
                "contact":"08166751719",
                "name":"Kelvin"
            },
            {
                "location":"Suleja/Mandalla",
                "contact":"08094165089",
                "name":"Kingsley"
            }
        ]
    }
}

CHURCHES = {

        "lagos mainland":{
            "name":"JFK EVENT CENTRE\nPlot 15, Block C, NERDC Rd, Opposite Tisco Plaza, Alausa, Ikeja.",
            "link":"https://goo.gl/maps/Jo455DQkk1M4eWGJ8"
        },
        "lagos island":{
            "name":"ROYAL OAKS CENTRE\nKm 14, Lekki Epe Expressway by Chisco Bus Stop, Enyo Petrol Station, Lekki.",
            "link":"https://g.page/royaloaksng?share"
        },
        "abuja":{
            "name":"EDEN PARKS AND GARDEN\nPlot 1126, Augustus Aikhomu Street, Opposite Chida Hotel, Utako, Abuja.",
            "link":"https://goo.gl/maps/oaF2CjMYC1rJ7KULA"
        },
        "port harcourt":{
            "name":"The AUTOGRAPH\n30, Sani Abacha Road, GRA Phase 3, Port Harcourt.",
            "link":"https://goo.gl/maps/fHCKSibeP6sAN1s16"
        },
        "ibadan":{
            "name":"TAFO ARENA EVENT CENTRE\nWAEC Road Junction, Polytechnic Road Oyo.",
            "link":"https://goo.gl/maps/335ejVk4wH34a8Sj7"
        }
}