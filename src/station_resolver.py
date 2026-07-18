from rapidfuzz import fuzz, process

from models import Station
from models import StationMatch
from normalizer import normalize_name


# Mapping of well-known station codes to alternate names
# used in the new dataset that are not present in the station master.
# This avoids wrong fuzzy matches caused by truncated canonical names.
EXTRA_ALIASES = {
    # Map station codes to new dataset names that don't match master canonical names
    # Format: "STATION_CODE": ["new dataset name 1", "new dataset name 2"]
    "DLI": ["Delhi", "Delhi Jn"],
    "PRYJ": ["Prayagraj Jn", "Prayagrajcheoki"],
    "DDU": ["Dd Upadhyaya Jn"],
    "LKO": ["Lucknow"],
    "NGP": ["Nagpur"],
    "MB": ["Moradabad"],
    "BE": ["Bareilly"],
    "KGP": ["Kharagpur Jn"],
    "RE": ["Rewari"],
    "CPR": ["Chhapra"],
    "BVI": ["Borivali"],
    "VZM": ["Vizianagram Jn"],
    "TCR": ["Thrisur"],
    "CLT": ["Kozhikkode"],
    "BAM": ["Brahmapur"],
    "QLN": ["Kollam Jn"],
    "PGT": ["Palakkad"],
    "TPJ": ["Tiruchchirappalli Jn"],
    "MKA": ["Mokameh Jn"],
    "BTI": ["Bhatinda Jn"],
    "INDB": ["Indore Jn Bg"],
    "BALU": ["Balugaon"],
    "SKZR": ["Sirpur Kaghaznagar"],
    "WADI": ["Wadi"],
    "RDM": ["Ramagundam"],
    "BKSC": ["Bokaro Stl City"],
    "SID": ["Siddhapur"],
    "TLMR": ["Taliamura"],
    "VJPJ": ["Vijaypur Jammu"],
    "RGS": ["Ringas Jn"],
    "DNRP": ["Dungarpur"],
    "BVRT": ["Bhimavaram Town"],
    "BYC": ["Bellary Cantt"],
    "COA": ["Mookambika Road"],
    "RAY": ["Rayagada"],
    "CAPE": ["Thiruvananthapuram Central"],
    "VRL": ["Veraval"],
    "JBP": ["Jabalpur"],
    "UDZ": ["Udaipur City"],
    "KUDL": ["Kudal"],
    "KKW": ["Kankavli"],
    "SSS": ["Sawantwadi Road"],
    "CHI": ["Chiplun"],
    "KAWR": ["Karwar"],
    "BBS": ["Bhubaneswar"],
    "CTC": ["Cuttack"],
    "SBP": ["Sambalpur Jn"],
    "ROU": ["Rourkela Jn"],
    "JSG": ["Jharsuguda Jn"],
    "SHDM": ["S Hirdaramnagar"],
    "SMVB": ["Smvt Bengaluru"],
    "TIG": ["Titlagarh"],
    "SOG": ["Sogaria"],
    "GVR": ["Goresuar"],
    "HAD": ["Harippadu"],
    "KPV": ["Karunagapalli"],
    "LM": ["Limbdi"],
    "YLM": ["Ellamanchiii"],
    "VGLJ": ["Virangana Lakshmibai"],
    "LTT": ["Lokmanyatilak"],
    "KYQ": ["Kamakhya"],
    "BCT": ["Mumbai Central"],
    "AWY": ["Aluva"],
    "MAS": ["Mgr Chennai Ctr"],
    "SBC": ["Ksr Bengaluru"],
    "BDTS": ["Bandra Terminus"],
    "CSMT": ["C Shivaji Maharaj T"],
    "NED": ["H Sahib Nanded"],
    "UMB": ["Ambala Cant Jn"],
    "UBL": ["Hubballi Jn"],
    "YPR": ["Yasvantpur Jn"],
    "BWN": ["Barddhaman"],
    "TNA": ["Thane"],
    "PNVL": ["Panvel"],
    "KYN": ["Kalyan Jn"],
    "BSR": ["Vasai Road"],
    "PUNE": ["Pune Jn"],
    "MAO": ["Madgaon"],
    "ANG": ["Ahilyanagar"],
    "KLBG": ["Kalaburagi"],
    "GADJ": ["Gandhinagar Jaipur"],
    "DEE": ["Delhi S Rohilla"],
    "TDD": ["Tadepalligudem"],
    "CPH": ["Champa"],
    "TJ": ["Thanjavur"],
    "MHRD": ["Mahemadavad Kheda Road"],
    "MALB": ["Maliya Miyana Jn"],
    "MNM": ["Manamadurai Jn"],
    "MKB": ["Mukhtiar Balwar"],
    "NKMJ": ["New Karimganj"],
    "RMT": ["Ramgarh Cantt"],
    "RPZ": ["Ranapratapnagar"],
    "SIOB": ["Samakhiali Jn"],
    "SRGM": ["Sardargram"],
    "SMLR": ["Shamlaji Road"],
    "SHU": ["Sholinghur"],
    "SRGT": ["Surendranagar Gate"],
    "ADRA": ["Adra Jn"],
    "YJUD": ["Yamunanagar Jagadhri"],
    "GMO": ["Gomoh Jn"],
    "SZP": ["Shahjehanpur"],
    "ANVT": ["Anand Vihar Terminal"],
    "RJQ": ["Rajendranagar T"],
    "MAJN": ["Mangalore Jn"],
    "DD": ["Daund Chord Lin"],
    "CD": ["Chandrapur Maharashtra"],
    "CKP": ["Chakradharpur"],
    "STP": ["Sitapur Jn"],
    "BGM": ["Belagavi"],
    "PNR": ["Panagarh"],
    "CGNR": ["Changanaseri"],
    "MBD": ["Maa Belha Devi Dham Pratapgarh Jn"],
    "KSJ": ["Kasganj"],
    "BNW": ["Bhiwani"],
    "BUP": ["Bhilai Power House"],
    "CSB": ["C Sambhajinagar"],
    "SEGM": ["Sevagram"],
    "LNE": ["Lucknow Ne"],
    "KRNT": ["Kurnool City"],
    "NRPD": ["Narmadapuram"],
    "JIA": ["Janjgir Naila"],
    "JPE": ["Jalpaiguri Road"],
    "HMO": ["Hanumangarh Jn"],
    "APDJ": ["Alipur Duar Jn"],
    "PRLI": ["Parli Vaijnath"],
    "SVKD": ["Shmata Vd Katra"],
    "BJP": ["Vijayapura"],
    "FDN": ["Faridabad New Town"],
    "RMD": ["Ramanathapuram"],
    "HNL": ["Hingoli Deccan"],
    "UMR": ["Umargam Road"],
    "KOLR": ["Kaikolur"],
    "TVCN": ["Thiruvananthapuram North"],
    "PDW": ["Pindwara"],
    "HPT": ["Hosapete Jn"],
    "TP": ["Tiruchchirapalli Fort"],
    "VSKP": ["Visakhapatnam"],
    "KRPU": ["Koraput"],
    "JGM": ["Jharsuguda Jn"],
    "BSP": ["Bilaspur Jn"],
    "R": ["Raipur Jn"],
    "DURG": ["Durg"],
    "BIA": ["Bilaspur"],
    "GGD": ["Guneru"],
    "NBD": ["Nabinagar"],
    "BXR": ["Buxar"],
    "ANGL": ["Angul"],
    "KRP": ["Koraput"],
    "BOD": ["Bonaigaon"],
    "GWV": ["Gorakhpur"],
    "MZP": ["Mirzapur"],
    "BSB": ["Varanasi"],
    "PRD": ["Phaphamau"],
    "JNU": ["Jaunpur Jn"],
    "SBT": ["Sabarmati"],
    "ND": ["Nadiad"],
    "BND": ["Bandra"],
    "STM": ["Surat"],
    "VAPI": ["Vapi"],
    "BRD": ["Bharuch"],
    "ADH": ["Andheri"],
    "BVI": ["Borivali"],
    "D": ["Dadar"],
    "M": ["Matunga"],
    "S": ["Sion"],
    "TT": ["Titwala"],
    "K": ["Kalyan"],
    "AS": ["Ambarnath"],
    "BDTS": ["Bandra Terminus"],
    "MMCT": ["Mumbai Central"],
    "MN": ["Mira Road"],
    "SKZR": ["Sirpur Kaghaznagar"],
    "KAK": ["Kakrani"],
    "SGNR": ["Sriganganagar"],
    "BKI": ["Barkakana"],
    "BAA": ["Balia"],
    "BAP": ["Beliaghata"],
}


class StationResolver:

    def __init__(self, station_master_df):

        self.code_index = {}
        self.canonical_index = {}
        self.alias_index = {}
        self.prefix_index = []

        for _, row in station_master_df.iterrows():

            code = str(row["Station Code"]).strip()

            canonical = str(row["Canonical Name"]).strip()

            normalized = normalize_name(canonical)

            aliases = []

            alias_text = str(
                row.get("Aliases", "")
            ).strip()

            if alias_text:

                aliases = [

                    alias.strip()

                    for alias in alias_text.split(";")

                    if alias.strip()

                ]

            # Also inject well-known alternate names so resolver
            # can match new dataset names without fuzzy guesswork.
            extra = EXTRA_ALIASES.get(code, [])
            aliases.extend(extra)

            station = Station(

                code=code,

                canonical_name=canonical,

                normalized_name=normalized,

                aliases=aliases

            )

            self.code_index[code] = station

            self.canonical_index[
                normalized
            ] = station

            self.prefix_index.append(
                station
            )

            for alias in aliases:

                self.alias_index[
                    normalize_name(alias)
                ] = station

    # ----------------------------------------------------

    def resolve(self, station_name):

        query = normalize_name(station_name)

        if not query:

            return StationMatch(False)

        #
        # Exact
        #

        station = self.canonical_index.get(query)

        if station:

            return StationMatch(

                matched=True,

                station_code=station.code,

                canonical_name=station.canonical_name,

                method="EXACT",

                confidence=100

            )

        #
        # Alias
        #

        station = self.alias_index.get(query)

        if station:

            return StationMatch(

                matched=True,

                station_code=station.code,

                canonical_name=station.canonical_name,

                method="ALIAS",

                confidence=100

            )

        #
        # Prefix
        #

        matches = []

        for station in self.prefix_index:

            if (

                station.normalized_name.startswith(query)

                or

                query.startswith(
                    station.normalized_name
                )

            ):

                matches.append(station)

        if len(matches) == 1:

            station = matches[0]

            return StationMatch(

                matched=True,

                station_code=station.code,

                canonical_name=station.canonical_name,

                method="PREFIX",

                confidence=100

            )

        #
        # Fuzzy
        #

        result = process.extractOne(

            query,

            self.canonical_index.keys(),

            scorer=fuzz.WRatio

        )

        if result:

            matched_name, score, _ = result

            if score >= 80:

                station = self.canonical_index[
                    matched_name
                ]

                return StationMatch(

                    matched=True,

                    station_code=station.code,

                    canonical_name=station.canonical_name,

                    method="FUZZY",

                    confidence=round(score, 2)

                )

        #
        # Suggestions
        #

        suggestions = process.extract(

            query,

            self.canonical_index.keys(),

            scorer=fuzz.WRatio,

            limit=5

        )

        return StationMatch(

            matched=False,

            suggestions=[

                self.canonical_index[
                    name
                ].canonical_name

                for name, _, _ in suggestions

            ]

        )

    # ----------------------------------------------------

    def resolve_code(self, code):

        return self.code_index.get(code)