"""DRAFT translations written by an AI assistant, NOT reviewed. Generates content/phrases/{fr,sw,ha,yo}.json
with "reviewed": false, so the gateway hides them until a native speaker approves them.
Hausa and Yoruba drafts in particular WILL contain errors: treat them as a starting point for the reviewer.

    python tools/draft_packs.py          # writes the four files
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "content" / "phrases"

T = {}

T["fr"] = dict(
    lang_name="Français",
    ui=dict(
        welcome="Bienvenue sur AcousticAcre.", choose_language="Choisissez la langue", choose_crop="Quelle culture ?",
        invalid="Choix invalide. Réessayez.", yes="Oui", no="Non",
        not_sure="Pas sûr. Ces signes ne correspondent pas à une seule maladie.",
        sms_sent="Conseils envoyés par SMS.",
        repeat_or_help="Tapez 1 pour réécouter, 2 pour recevoir les conseils par SMS, 9 pour parler à un agent agricole.",
        connecting="Nous vous mettons en relation avec un agent agricole.",
        no_officer="Aucun agent n'est disponible. Appelez votre service de vulgarisation local.",
        goodbye="Merci. Au revoir.", disclaimer="Conseil, pas une garantie.",
        help_line="Aide : appelez le [numéro d'aide].", press_option="Tapez {n} pour {option}.",
        no_input="Nous n'avons pas reçu votre réponse. Rappelez, s'il vous plaît.",
        retake_blurry="Photo floue. Tenez le téléphone immobile et reprenez.",
        retake_dark="Photo trop sombre. Allez vers plus de lumière.",
        retake_bright="Photo trop claire. Mettez la feuille à l'ombre et reprenez.",
        retake_no_leaf="Aucune feuille trouvée. Remplissez la photo avec une feuille.",
        retake_too_quiet="Rapprochez le téléphone de la machine.", retake_clipping="Éloignez un peu le téléphone.",
        retake_wind="Protégez le micro du vent.", retake_no_machine="Machine non détectée. Est-elle en marche ?",
        where_model_looked="En surbrillance : là où le modèle a regardé."),
    crops=dict(cassava="Manioc", maize="Maïs", tomato="Tomate"),
    questions=dict(
        q_leaves_twisted="Les feuilles sont-elles tordues, enroulées ou déformées ?",
        q_yellow_green_patches="Les feuilles ont-elles des taches jaunes et vertes mélangées ?",
        q_yellow_along_veins="Y a-t-il des taches jaunes le long des nervures des vieilles feuilles du bas ?",
        q_brown_streak_or_root_rot="Y a-t-il des stries brunes sur les tiges vertes, ou une pourriture brune dans les racines ?",
        q_wet_spots_or_wilting="Y a-t-il des taches anguleuses d'aspect mouillé, ou des pousses qui fanent et meurent ?",
        q_tiny_yellow_dots="Les feuilles sont-elles pâles avec de petits points jaunes, et celles du haut petites et serrées ?",
        q_ragged_holes_frass="Y a-t-il des trous irréguliers dans les feuilles et des déjections comme de la sciure au centre ?",
        q_powdery_rust_spots="Y a-t-il de petites taches poudreuses brun-rouge qui restent sur le doigt ?",
        q_long_grey_lesions="Y a-t-il de longues taches grises ou beiges, en forme de cigare ?",
        q_broken_yellow_streaks="Y a-t-il de fines stries jaunes ou blanches interrompues le long des nervures ?",
        q_sudden_wilt_green="La plante entière fane-t-elle vite alors que ses feuilles sont encore vertes ?",
        q_small_curled_yellow_edges="Les feuilles sont-elles petites, enroulées vers le haut, avec des bords jaunes ?",
        q_leaf_mines_fruit_holes="Y a-t-il des galeries pâles dans les feuilles, ou de petits trous dans les fruits ?",
        q_dark_wet_patches_spread="Y a-t-il de grandes taches sombres d'aspect mouillé qui s'étendent vite après la pluie ?",
        q_target_ring_spots="Y a-t-il des taches brunes avec des anneaux, comme une cible, sur les feuilles du bas ?"),
    diagnoses=dict(
        cassava_mosaic="Mosaïque du manioc probable", cassava_brown_streak="Striure brune du manioc probable",
        cassava_bacterial_blight="Bactériose du manioc probable", cassava_green_mite="Acarien vert du manioc probable",
        machine_healthy="La machine semble normale", machine_fault="La machine a peut-être une panne",
        maize_fall_armyworm="Chenille légionnaire d'automne probable", maize_common_rust="Rouille commune probable",
        maize_northern_leaf_blight="Helminthosporiose du maïs probable", maize_streak_virus="Virus de la striure du maïs probable",
        tomato_bacterial_wilt="Flétrissement bactérien probable", tomato_yellow_leaf_curl="Virus de l'enroulement jaune de la tomate probable",
        tomato_tuta_absoluta="Mineuse de la tomate (Tuta absoluta) probable", tomato_late_blight="Mildiou probable",
        tomato_early_blight="Alternariose probable", cassava_healthy="La feuille de manioc semble saine",
        maize_healthy="La feuille de maïs semble saine", maize_gray_leaf_spot="Cercosporiose du maïs probable",
        tomato_healthy="La feuille de tomate semble saine", tomato_other_leaf_problem="Maladie probable de la feuille de tomate, type incertain"),
    steps=dict(
        remove_infected_plants="Arrachez et détruisez les plantes malades.", use_clean_cuttings="Plantez seulement des boutures de plantes saines.",
        plant_tolerant_variety="Demandez une variété tolérante pour la saison prochaine.",
        do_not_share_cuttings="Ne donnez ni ne prenez de boutures de ce champ.",
        harvest_early_check_roots="Vérifiez les racines et récoltez tôt si elles sont touchées.",
        clean_tools="Nettoyez les outils de coupe entre les plantes.", check_underside_leaves="Regardez sous les feuilles pour trouver de petits acariens.",
        keep_field_weeded="Gardez le champ désherbé.", ask_extension_officer="Montrez la plante à un agent agricole.",
        keep_regular_service="Gardez l'entretien régulier.", rescan_if_sound_changes="Refaites un scan si le bruit change.",
        stop_machine="Arrêtez la machine si c'est sans danger.", check_mounting_bolts="Vérifiez que les boulons de fixation sont serrés.",
        check_belts_and_bearings="Vérifiez l'usure des courroies et des roulements.",
        contact_mechanic="Appelez un mécanicien avant de la faire tourner longtemps.",
        check_whorls_morning="Regardez le cœur des jeunes plants tôt le matin.",
        crush_eggs_and_larvae="Écrasez à la main les œufs et les chenilles.",
        ask_officer_approved_control="Demandez à un agent agricole un traitement autorisé. Suivez l'étiquette.",
        remove_crop_residue="Enlevez ou enfouissez les restes de culture après la récolte.",
        rotate_crops="Ne replantez pas la même culture à cet endroit la saison prochaine.",
        plant_with_neighbours="Semez en même temps que les champs voisins la saison prochaine.",
        control_weeds="Limitez les herbes autour du champ.",
        remove_wilted_with_soil="Arrachez les plantes fanées avec la terre autour des racines et détruisez-les.",
        no_solanaceae_next_season="Ne plantez ni tomate, ni piment, ni aubergine ici la saison prochaine.",
        use_insect_net="Protégez les jeunes plants avec un filet anti-insectes.",
        destroy_infested_leaves_fruit="Cueillez et détruisez les feuilles et fruits abîmés.",
        use_pheromone_traps="Renseignez-vous sur les pièges à phéromones contre ce ravageur.",
        remove_infected_leaves="Enlevez et détruisez les feuilles malades.", water_soil_not_leaves="Arrosez le sol, pas les feuilles.",
        space_plants="Espacez les plantes pour laisser passer l'air.", mulch_soil="Couvrez le sol de paillis pour éviter les éclaboussures.",
        plant_resistant_variety="Plantez une variété résistante la saison prochaine.",
        keep_checking_weekly="Continuez à surveiller vos plantes chaque semaine."))

T["sw"] = dict(
    lang_name="Kiswahili",
    ui=dict(
        welcome="Karibu AcousticAcre.", choose_language="Chagua lugha", choose_crop="Zao gani?",
        invalid="Chaguo si sahihi. Jaribu tena.", yes="Ndiyo", no="Hapana",
        not_sure="Hatuna uhakika. Dalili hizi hazilingani na ugonjwa mmoja.", sms_sent="Ushauri umetumwa kwa SMS.",
        repeat_or_help="Bonyeza 1 kurudia, 2 kupata ushauri kwa SMS, 9 kuongea na afisa ugani.",
        connecting="Tunakuunganisha na afisa ugani.",
        no_officer="Hakuna afisa kwa sasa. Tafadhali piga ofisi ya ugani iliyo karibu.",
        goodbye="Asante. Kwaheri.", disclaimer="Ni ushauri, si uhakika.",
        help_line="Kwa msaada piga [namba ya msaada].", press_option="Bonyeza {n} kwa {option}.",
        no_input="Hatukupata jibu lako. Tafadhali piga tena.",
        retake_blurry="Picha haiko wazi. Shika simu bila kutikisa upige tena.",
        retake_dark="Picha ni giza sana. Nenda kwenye mwanga zaidi.",
        retake_bright="Picha ina mwanga mwingi. Weka kivuli kwenye jani upige tena.",
        retake_no_leaf="Hakuna jani. Jaza picha kwa jani moja.",
        retake_too_quiet="Sogeza simu karibu na mashine.", retake_clipping="Sogeza simu mbali kidogo.",
        retake_wind="Kinga kipaza sauti dhidi ya upepo.", retake_no_machine="Mashine haijasikika. Je, inafanya kazi?",
        where_model_looked="Sehemu iliyoangaziwa: mahali mfumo ulipoangalia."),
    crops=dict(cassava="Muhogo", maize="Mahindi", tomato="Nyanya"),
    questions=dict(
        q_leaves_twisted="Je, majani yamepinda, yamejikunja au yameharibika umbo?",
        q_yellow_green_patches="Je, majani yana mabaka ya njano na kijani yaliyochanganyika?",
        q_yellow_along_veins="Je, kuna mabaka ya njano kando ya mishipa ya majani ya chini, yaliyokomaa?",
        q_brown_streak_or_root_rot="Je, kuna michirizi ya kahawia kwenye mashina mabichi, au kuoza kwa kahawia ndani ya mizizi?",
        q_wet_spots_or_wilting="Je, kuna madoa yenye pembe yanayoonekana kama yamelowa, au vichipukizi vinavyonyauka na kufa?",
        q_tiny_yellow_dots="Je, majani yamefifia yenye vidoti vidogo vya njano, na majani ya juu ni madogo na yamebanana?",
        q_ragged_holes_frass="Je, kuna matundu yasiyo sawa kwenye majani na kinyesi kama unga wa mbao katikati?",
        q_powdery_rust_spots="Je, kuna madoa madogo ya unga mwekundu-kahawia yanayobaki kwenye kidole?",
        q_long_grey_lesions="Je, kuna mabaka marefu ya kijivu au hudhurungi, yenye umbo la sigara?",
        q_broken_yellow_streaks="Je, kuna michirizi myembamba ya njano au nyeupe iliyokatikakatika kando ya mishipa?",
        q_sudden_wilt_green="Je, mmea mzima unanyauka haraka wakati majani bado ni ya kijani?",
        q_small_curled_yellow_edges="Je, majani ni madogo, yamejikunja juu, na kingo za njano?",
        q_leaf_mines_fruit_holes="Je, kuna njia nyeupe zinazozunguka ndani ya majani, au matundu madogo kwenye matunda?",
        q_dark_wet_patches_spread="Je, kuna mabaka makubwa meusi kama yamelowa yanayoenea haraka baada ya mvua?",
        q_target_ring_spots="Je, kuna madoa ya kahawia yenye duara kama shabaha kwenye majani ya chini?"),
    diagnoses=dict(
        cassava_mosaic="Huenda ni ugonjwa wa batobato wa muhogo", cassava_brown_streak="Huenda ni ugonjwa wa michirizi ya kahawia wa muhogo",
        cassava_bacterial_blight="Huenda ni ugonjwa wa bakteria wa muhogo", cassava_green_mite="Huenda ni utitiri wa kijani wa muhogo",
        machine_healthy="Mashine inasikika kawaida", machine_fault="Huenda mashine ina hitilafu",
        maize_fall_armyworm="Huenda ni viwavijeshi vamizi", maize_common_rust="Huenda ni kutu ya mahindi",
        maize_northern_leaf_blight="Huenda ni ugonjwa wa madoa marefu ya majani (northern leaf blight)",
        maize_streak_virus="Huenda ni virusi vya michirizi ya mahindi", tomato_bacterial_wilt="Huenda ni mnyauko bakteria",
        tomato_yellow_leaf_curl="Huenda ni virusi vya kukunjamana kwa majani ya nyanya", tomato_tuta_absoluta="Huenda ni kantangaze (Tuta absoluta)",
        tomato_late_blight="Huenda ni baridi kali ya nyanya (late blight)", tomato_early_blight="Huenda ni ukungu wa mapema (early blight)",
        cassava_healthy="Jani la muhogo linaonekana zima", maize_healthy="Jani la mahindi linaonekana zima",
        maize_gray_leaf_spot="Huenda ni madoa ya kijivu ya majani", tomato_healthy="Jani la nyanya linaonekana zima",
        tomato_other_leaf_problem="Huenda ni ugonjwa wa jani la nyanya, aina haijulikani"),
    steps=dict(
        remove_infected_plants="Ng'oa na uharibu mimea yenye ugonjwa.", use_clean_cuttings="Panda vipandikizi kutoka mimea mizima tu.",
        plant_tolerant_variety="Uliza aina inayostahimili kwa msimu ujao.", do_not_share_cuttings="Usitoe wala kuchukua vipandikizi kutoka shamba hili.",
        harvest_early_check_roots="Kagua mizizi na uvune mapema ikiwa imeathirika.", clean_tools="Safisha vifaa vya kukatia kati ya mmea mmoja na mwingine.",
        check_underside_leaves="Angalia chini ya majani kuona utitiri wadogo.", keep_field_weeded="Weka shamba bila magugu.",
        ask_extension_officer="Mwonyeshe afisa ugani mmea huu.", keep_regular_service="Endelea na ratiba ya kawaida ya matengenezo.",
        rescan_if_sound_changes="Pima tena kama sauti itabadilika.", stop_machine="Zima mashine kama ni salama kufanya hivyo.",
        check_mounting_bolts="Hakikisha boliti za kushikilia zimekazwa.", check_belts_and_bearings="Kagua mikanda na beringi kama zimechakaa.",
        contact_mechanic="Mpigie fundi kabla ya kuiendesha kwa muda mrefu.",
        check_whorls_morning="Kagua katikati ya mimea michanga asubuhi na mapema.",
        crush_eggs_and_larvae="Ponda mayai na viwavi kwa mkono.",
        ask_officer_approved_control="Muulize afisa ugani kuhusu dawa zilizoidhinishwa. Fuata maelekezo ya lebo.",
        remove_crop_residue="Ondoa au fukia mabaki ya mimea baada ya mavuno.",
        rotate_crops="Usipande zao lilelile mahali hapa msimu ujao.",
        plant_with_neighbours="Panda wakati mmoja na mashamba ya jirani msimu ujao.",
        control_weeds="Punguza nyasi kuzunguka shamba.",
        remove_wilted_with_soil="Ng'oa mimea iliyonyauka pamoja na udongo wa mizizi na uiharibu.",
        no_solanaceae_next_season="Usipande nyanya, pilipili wala biringanya hapa msimu ujao.",
        use_insect_net="Linda miche kwa neti ya kuzuia wadudu.", destroy_infested_leaves_fruit="Chuma na uharibu majani na matunda yaliyoharibika.",
        use_pheromone_traps="Uliza kuhusu mitego ya feromoni kwa mdudu huyu.", remove_infected_leaves="Ondoa na uharibu majani yenye ugonjwa.",
        water_soil_not_leaves="Mwagilia udongo, si majani.", space_plants="Acha nafasi zaidi kati ya mimea ili hewa ipite.",
        mulch_soil="Funika udongo kwa matandazo kuzuia matone kurukia majani.",
        plant_resistant_variety="Panda aina inayostahimili msimu ujao.", keep_checking_weekly="Endelea kukagua mimea yako kila wiki."))

T["ha"] = dict(
    lang_name="Hausa",
    ui=dict(
        welcome="Barka da zuwa AcousticAcre.", choose_language="Zaɓi harshe", choose_crop="Wane amfanin gona?",
        invalid="Zaɓin bai yi daidai ba. Sake gwadawa.", yes="Eh", no="A'a",
        not_sure="Ba mu da tabbas. Waɗannan alamu ba su dace da cuta ɗaya ba.", sms_sent="An aika matakai ta SMS.",
        repeat_or_help="Danna 1 don maimaitawa, 2 don karɓar matakai ta SMS, 9 don magana da jami'in gona.",
        connecting="Muna haɗa ka da jami'in gona.",
        no_officer="Babu jami'i a yanzu. Da fatan ka kira ofishin jami'an gona na kusa.",
        goodbye="Na gode. Sai an jima.", disclaimer="Shawara ce, ba tabbaci ba.",
        help_line="Don taimako kira [lambar taimako].", press_option="Danna {n} don {option}.",
        no_input="Ba mu sami amsarka ba. Da fatan ka sake kira.",
        retake_blurry="Hoton bai fito sosai ba. Riƙe wayar a tsaye ka sake ɗauka.",
        retake_dark="Hoton ya yi duhu sosai. Matsa zuwa wurin da haske.",
        retake_bright="Hoton ya yi haske sosai. Sanya inuwa a kan ganyen ka sake ɗauka.",
        retake_no_leaf="Ba a ga ganye ba. Cika hoton da ganye ɗaya.",
        retake_too_quiet="Kawo wayar kusa da injin.", retake_clipping="Ɗan nisanta wayar kaɗan.",
        retake_wind="Kare makirufo daga iska.", retake_no_machine="Ba a ji injin ba. Shin yana aiki?",
        where_model_looked="Wurin da aka haskaka: inda tsarin ya duba."),
    crops=dict(cassava="Rogo", maize="Masara", tomato="Tumatur"),
    questions=dict(
        q_leaves_twisted="Ganyayyaki sun murɗe, sun naɗe ko sun lalace?",
        q_yellow_green_patches="Ganyayyaki suna da tabo masu ruwan ɗorawa da kore a gauraye?",
        q_yellow_along_veins="Akwai tabo masu ruwan ɗorawa a gefen jijiyoyin tsofaffin ganyayyaki na ƙasa?",
        q_brown_streak_or_root_rot="Akwai layuka masu ruwan ƙasa a kan kara kore, ko ruɓewa mai ruwan ƙasa a cikin saiwa?",
        q_wet_spots_or_wilting="Akwai tabo masu kusurwa da suka yi kamar sun jiƙe, ko ƙarshen tsiro yana yaushi yana mutuwa?",
        q_tiny_yellow_dots="Ganyayyaki sun kode da ƙananan ɗigo masu ruwan ɗorawa, kuma ganyen sama ƙanana ne a haɗe?",
        q_ragged_holes_frass="Akwai ramuka marasa tsari a ganye da kashi kamar garin katako a tsakiya?",
        q_powdery_rust_spots="Akwai ƙananan tabo masu gari ja-ruwan ƙasa da ke manne wa yatsa?",
        q_long_grey_lesions="Akwai dogayen tabo masu launin toka ko ruwan ƙasa mai haske, kamar sigari?",
        q_broken_yellow_streaks="Akwai siraran layuka masu ruwan ɗorawa ko fari da suka katse a gefen jijiyoyin ganye?",
        q_sudden_wilt_green="Dukan shukar tana yaushi da sauri alhali ganyayyakinta har yanzu kore ne?",
        q_small_curled_yellow_edges="Ganyayyaki ƙanana ne, sun naɗe zuwa sama, da gefuna masu ruwan ɗorawa?",
        q_leaf_mines_fruit_holes="Akwai hanyoyi farare masu karkata a cikin ganye, ko ƙananan ramuka a 'ya'yan itace?",
        q_dark_wet_patches_spread="Akwai manyan tabo baƙaƙe kamar sun jiƙe da ke yaɗuwa da sauri bayan ruwan sama?",
        q_target_ring_spots="Akwai tabo masu ruwan ƙasa da zobba kamar abin harbi a ganyayyakin ƙasa?"),
    diagnoses=dict(
        cassava_mosaic="Mai yiwuwa cutar mosaic ta rogo", cassava_brown_streak="Mai yiwuwa cutar layukan ruwan ƙasa ta rogo",
        cassava_bacterial_blight="Mai yiwuwa cutar ƙwayoyin cuta ta rogo", cassava_green_mite="Mai yiwuwa ƙwarin green mite na rogo",
        machine_healthy="Injin yana jin kamar lafiya", machine_fault="Mai yiwuwa injin yana da matsala",
        maize_fall_armyworm="Mai yiwuwa tsutsar fall armyworm", maize_common_rust="Mai yiwuwa cutar tsatsa ta masara",
        maize_northern_leaf_blight="Mai yiwuwa cutar dogayen tabo ta ganyen masara", maize_streak_virus="Mai yiwuwa ƙwayar cutar layuka ta masara",
        tomato_bacterial_wilt="Mai yiwuwa yaushin ƙwayoyin cuta", tomato_yellow_leaf_curl="Mai yiwuwa ƙwayar cutar naɗewar ganyen tumatur",
        tomato_tuta_absoluta="Mai yiwuwa ƙwarin Tuta absoluta", tomato_late_blight="Mai yiwuwa cutar late blight",
        tomato_early_blight="Mai yiwuwa cutar early blight", cassava_healthy="Ganyen rogo yana da lafiya",
        maize_healthy="Ganyen masara yana da lafiya", maize_gray_leaf_spot="Mai yiwuwa cutar tabo masu launin toka",
        tomato_healthy="Ganyen tumatur yana da lafiya", tomato_other_leaf_problem="Mai yiwuwa cutar ganyen tumatur, ba a san iri ba"),
    steps=dict(
        remove_infected_plants="Tumɓuke ka lalata shuke-shuken da ke da cuta.", use_clean_cuttings="Shuka kara daga shuke-shuke masu lafiya kawai.",
        plant_tolerant_variety="Nemi irin da ke jure cuta don damina mai zuwa.", do_not_share_cuttings="Kada ka bayar ko karɓi kara daga wannan gona.",
        harvest_early_check_roots="Duba saiwoyi ka girbe da wuri idan sun kamu.", clean_tools="Wanke kayan yanka tsakanin shuka da shuka.",
        check_underside_leaves="Duba ƙarƙashin ganye don ƙananan ƙwari.", keep_field_weeded="Kiyaye gona babu ciyawa.",
        ask_extension_officer="Nuna wa jami'in gona shukar.", keep_regular_service="Ci gaba da gyaran injin akai-akai.",
        rescan_if_sound_changes="Sake gwadawa idan sautin ya canza.", stop_machine="Kashe injin idan babu haɗari.",
        check_mounting_bolts="Tabbatar ƙusoshin da ke riƙe injin sun matsu.", check_belts_and_bearings="Duba bel da bearing ko sun lalace.",
        contact_mechanic="Kira makaniki kafin ka daɗe kana amfani da shi.",
        check_whorls_morning="Duba tsakiyar ƙananan shuke-shuke da sassafe.", crush_eggs_and_larvae="Murƙushe ƙwai da tsutsotsi da hannu.",
        ask_officer_approved_control="Tambayi jami'in gona game da maganin da aka amince da shi. Bi umarnin kwali.",
        remove_crop_residue="Cire ko binne ragowar shuke-shuke bayan girbi.",
        rotate_crops="Kada ka shuka amfanin gona ɗaya a wannan wuri a damina mai zuwa.",
        plant_with_neighbours="Shuka a lokaci ɗaya da gonakin makwabta a damina mai zuwa.",
        control_weeds="Rage ciyawa a kewayen gona.",
        remove_wilted_with_soil="Tumɓuke shuke-shuken da suka yi yaushi tare da ƙasar saiwa ka lalata su.",
        no_solanaceae_next_season="Kada ka shuka tumatur, barkono ko gauta a nan a damina mai zuwa.",
        use_insect_net="Kare ƙananan shuke-shuke da ragar hana ƙwari.", destroy_infested_leaves_fruit="Tsinka ka lalata ganye da 'ya'yan da suka lalace.",
        use_pheromone_traps="Tambayi game da tarkon pheromone na wannan ƙwarin.", remove_infected_leaves="Cire ka lalata ganyayyakin da ke da cuta.",
        water_soil_not_leaves="Zuba ruwa a ƙasa, ba a kan ganye ba.", space_plants="Ba shuke-shuke ƙarin fili don iska ta wuce.",
        mulch_soil="Rufe ƙasa da ciyawa don hana fantsamar ruwa.",
        plant_resistant_variety="Shuka irin da ke jure cuta a damina mai zuwa.", keep_checking_weekly="Ci gaba da duba shuke-shukenka kowane mako."))

T["yo"] = dict(
    lang_name="Yorùbá",
    ui=dict(
        welcome="Ẹ kú àbọ̀ sí AcousticAcre.", choose_language="Yan èdè", choose_crop="Irú ohun ọ̀gbìn wo?",
        invalid="Àṣàyàn kò tọ̀nà. Tún gbìyànjú.", yes="Bẹ́ẹ̀ ni", no="Rárá",
        not_sure="A kò dá wa lójú. Àwọn àmì wọ̀nyí kò bá àìsàn kan ṣoṣo mu.", sms_sent="A ti fi ìmọ̀ràn ránṣẹ́ nípasẹ̀ SMS.",
        repeat_or_help="Tẹ 1 láti tún gbọ́, 2 láti gba ìmọ̀ràn nípasẹ̀ SMS, 9 láti bá òṣìṣẹ́ àgbẹ̀ sọ̀rọ̀.",
        connecting="À ń so ọ́ pọ̀ mọ́ òṣìṣẹ́ àgbẹ̀.",
        no_officer="Kò sí òṣìṣẹ́ báyìí. Jọ̀wọ́ pe ọ́fíìsì àwọn òṣìṣẹ́ àgbẹ̀ tó súnmọ́ ọ.",
        goodbye="Ẹ ṣé. Ó dàbọ̀.", disclaimer="Ìmọ̀ràn ni, kì í ṣe ìdánilójú.",
        help_line="Fún ìrànlọ́wọ́ pe [nọ́mbà ìrànlọ́wọ́].", press_option="Tẹ {n} fún {option}.",
        no_input="A kò gbọ́ ìdáhùn rẹ. Jọ̀wọ́ tún pè.",
        retake_blurry="Àwòrán kò mọ́. Di fóònù mú dáadáa kí o tún yà á.",
        retake_dark="Àwòrán ṣókùnkùn jù. Lọ sí ibi tí ìmọ́lẹ̀ wà.",
        retake_bright="Ìmọ́lẹ̀ pọ̀ jù nínú àwòrán. Ṣíji bo ewé kí o tún yà á.",
        retake_no_leaf="A kò rí ewé. Jẹ́ kí ewé kan kún àwòrán.",
        retake_too_quiet="Mú fóònù súnmọ́ ẹ̀rọ náà.", retake_clipping="Gbé fóònù jìnnà díẹ̀.",
        retake_wind="Dáàbò bo máíkì lọ́wọ́ afẹ́fẹ́.", retake_no_machine="A kò gbọ́ ẹ̀rọ. Ṣé ó ń ṣiṣẹ́?",
        where_model_looked="Ibi tí a tàn ìmọ́lẹ̀ sí: ibi tí ètò náà wò."),
    crops=dict(cassava="Ẹ̀gẹ́", maize="Àgbàdo", tomato="Tòmátì"),
    questions=dict(
        q_leaves_twisted="Ṣé àwọn ewé ti yí, ká, tàbí bàjẹ́ ní ìrísí?",
        q_yellow_green_patches="Ṣé àwọn ewé ní àbàwọ́n pupa-ìyeyè àti àwọ̀ ewé tí ó dàpọ̀?",
        q_yellow_along_veins="Ṣé àbàwọ́n pupa-ìyeyè wà lẹ́gbẹ̀ẹ́ iṣan àwọn ewé àgbà ìsàlẹ̀?",
        q_brown_streak_or_root_rot="Ṣé ìlà àwọ̀ ilẹ̀ wà lórí igi tútù, tàbí jíjẹrà àwọ̀ ilẹ̀ nínú gbòǹgbò?",
        q_wet_spots_or_wilting="Ṣé àbàwọ́n onígun tí ó dàbí ẹni pé ó tutù wà, tàbí orí ọ̀mùnú ń rọ tí ó sì ń kú?",
        q_tiny_yellow_dots="Ṣé àwọn ewé ti ṣá, pẹ̀lú àmì kékeré pupa-ìyeyè, tí ewé òkè sì kéré tí wọ́n sì kóra jọ?",
        q_ragged_holes_frass="Ṣé ihò wà nínú ewé, pẹ̀lú ìgbẹ́ tí ó dàbí ìyẹ̀fun igi ní àárín?",
        q_powdery_rust_spots="Ṣé àbàwọ́n kékeré bí ìyẹ̀fun pupa-àwọ̀ ilẹ̀ wà tí ó ń lẹ̀ mọ́ ìka?",
        q_long_grey_lesions="Ṣé àbàwọ́n gígùn àwọ̀ eérú tàbí àwọ̀ ilẹ̀ fẹ́ẹ́rẹ́ wà, bí sìgá?",
        q_broken_yellow_streaks="Ṣé ìlà tínínrín pupa-ìyeyè tàbí funfun tí ó já wà lẹ́gbẹ̀ẹ́ iṣan ewé?",
        q_sudden_wilt_green="Ṣé gbogbo ọ̀gbìn náà ń rọ kíákíá nígbà tí ewé rẹ̀ ṣì jẹ́ àwọ̀ ewé?",
        q_small_curled_yellow_edges="Ṣé àwọn ewé kéré, wọ́n ká sókè, tí etí wọn sì jẹ́ pupa-ìyeyè?",
        q_leaf_mines_fruit_holes="Ṣé ọ̀nà funfun tí ó lọ́ wà nínú ewé, tàbí ihò kékeré nínú èso?",
        q_dark_wet_patches_spread="Ṣé àbàwọ́n dúdú ńlá tí ó dàbí ẹni pé ó tutù wà tí ó ń tàn kálẹ̀ kíákíá lẹ́yìn òjò?",
        q_target_ring_spots="Ṣé àbàwọ́n àwọ̀ ilẹ̀ pẹ̀lú òrùka bí àmì ìtafà wà lórí ewé ìsàlẹ̀?"),
    diagnoses=dict(
        cassava_mosaic="Ó ṣeé ṣe kí ó jẹ́ àrùn mosaic ẹ̀gẹ́", cassava_brown_streak="Ó ṣeé ṣe kí ó jẹ́ àrùn ìlà àwọ̀ ilẹ̀ ẹ̀gẹ́",
        cassava_bacterial_blight="Ó ṣeé ṣe kí ó jẹ́ àrùn bakitéríà ẹ̀gẹ́", cassava_green_mite="Ó ṣeé ṣe kí ó jẹ́ kòkòrò green mite ẹ̀gẹ́",
        machine_healthy="Ìró ẹ̀rọ dàbí ẹni pé ó dára", machine_fault="Ó ṣeé ṣe kí ẹ̀rọ ní àbùkù",
        maize_fall_armyworm="Ó ṣeé ṣe kí ó jẹ́ kòkòrò fall armyworm", maize_common_rust="Ó ṣeé ṣe kí ó jẹ́ àrùn ìpẹtà àgbàdo",
        maize_northern_leaf_blight="Ó ṣeé ṣe kí ó jẹ́ àrùn àbàwọ́n gígùn ewé àgbàdo", maize_streak_virus="Ó ṣeé ṣe kí ó jẹ́ fáírọ́ọ̀sì ìlà àgbàdo",
        tomato_bacterial_wilt="Ó ṣeé ṣe kí ó jẹ́ àrùn rírọ bakitéríà", tomato_yellow_leaf_curl="Ó ṣeé ṣe kí ó jẹ́ fáírọ́ọ̀sì kíká ewé tòmátì",
        tomato_tuta_absoluta="Ó ṣeé ṣe kí ó jẹ́ kòkòrò Tuta absoluta", tomato_late_blight="Ó ṣeé ṣe kí ó jẹ́ àrùn late blight",
        tomato_early_blight="Ó ṣeé ṣe kí ó jẹ́ àrùn early blight", cassava_healthy="Ewé ẹ̀gẹ́ dàbí ẹni pé ó ní ìlera",
        maize_healthy="Ewé àgbàdo dàbí ẹni pé ó ní ìlera", maize_gray_leaf_spot="Ó ṣeé ṣe kí ó jẹ́ àrùn àbàwọ́n eérú",
        tomato_healthy="Ewé tòmátì dàbí ẹni pé ó ní ìlera", tomato_other_leaf_problem="Ó ṣeé ṣe kí ó jẹ́ àrùn ewé tòmátì, a kò mọ irú rẹ̀"),
    steps=dict(
        remove_infected_plants="Fa àwọn ọ̀gbìn tí ó ní àrùn tu kí o sì pa wọ́n run.", use_clean_cuttings="Gbin igi láti ara ọ̀gbìn tí ó ní ìlera nìkan.",
        plant_tolerant_variety="Béèrè irú tí ó lè fara da àrùn fún àsìkò tí ń bọ̀.",
        do_not_share_cuttings="Má ṣe fún ẹnikẹ́ni tàbí gba igi láti oko yìí.",
        harvest_early_check_roots="Ṣàyẹ̀wò gbòǹgbò kí o sì kórè ní kùtùkùtù tí wọ́n bá ti kó àrùn.",
        clean_tools="Fọ irinṣẹ́ gígé láàárín ọ̀gbìn kan sí èkejì.", check_underside_leaves="Wo abẹ́ ewé fún kòkòrò kékeré.",
        keep_field_weeded="Jẹ́ kí oko wà láìsí èpò.", ask_extension_officer="Fi ọ̀gbìn náà han òṣìṣẹ́ àgbẹ̀.",
        keep_regular_service="Máa tún ẹ̀rọ ṣe déédéé.", rescan_if_sound_changes="Tún ṣàyẹ̀wò tí ìró bá yí padà.",
        stop_machine="Pa ẹ̀rọ náà tí kò bá léwu.", check_mounting_bolts="Rí i dájú pé àwọn bóòtù tí ó di ẹ̀rọ mú le dáadáa.",
        check_belts_and_bearings="Ṣàyẹ̀wò bẹ́líìtì àti bíárìn bóyá wọ́n ti gbó.",
        contact_mechanic="Pe ẹlẹ́rọ kí o tó lò ó fún ìgbà pípẹ́.",
        check_whorls_morning="Ṣàyẹ̀wò àárín àwọn ọ̀gbìn kékeré ní àárọ̀ kùtùkùtù.", crush_eggs_and_larvae="Fi ọwọ́ tẹ ẹyin àti ìdin pa.",
        ask_officer_approved_control="Béèrè lọ́wọ́ òṣìṣẹ́ àgbẹ̀ nípa oògùn tí a fọwọ́ sí. Tẹ̀lé ìtọ́ni lórí àmì.",
        remove_crop_residue="Kó tàbí bo ìyókù ọ̀gbìn mọ́lẹ̀ lẹ́yìn ìkórè.",
        rotate_crops="Má ṣe gbin irú ọ̀gbìn kan náà síbí ní àsìkò tí ń bọ̀.",
        plant_with_neighbours="Gbìn ní àkókò kan náà pẹ̀lú àwọn oko tí ó wà nítòsí ní àsìkò tí ń bọ̀.",
        control_weeds="Dín koríko kù yíká oko.",
        remove_wilted_with_soil="Fa àwọn ọ̀gbìn tí ó rọ tu pẹ̀lú ilẹ̀ gbòǹgbò wọn kí o sì pa wọ́n run.",
        no_solanaceae_next_season="Má ṣe gbin tòmátì, ata tàbí ìkàn síbí ní àsìkò tí ń bọ̀.",
        use_insect_net="Fi àwọ̀n kòkòrò dáàbò bo àwọn ọ̀gbìn kékeré.",
        destroy_infested_leaves_fruit="Ká àwọn ewé àti èso tí ó ti bàjẹ́ kí o sì pa wọ́n run.",
        use_pheromone_traps="Béèrè nípa pańpẹ́ pheromone fún kòkòrò yìí.", remove_infected_leaves="Yọ àwọn ewé tí ó ní àrùn kí o sì pa wọ́n run.",
        water_soil_not_leaves="Bomi rin ilẹ̀, kì í ṣe ewé.", space_plants="Fi àyè sí i láàárín àwọn ọ̀gbìn kí afẹ́fẹ́ lè kọjá.",
        mulch_soil="Fi koríko gbígbẹ bo ilẹ̀ láti dènà ìtasí omi.",
        plant_resistant_variety="Gbin irú tí ó lè kojú àrùn ní àsìkò tí ń bọ̀.", keep_checking_weekly="Máa ṣàyẹ̀wò àwọn ọ̀gbìn rẹ ní ọ̀sẹ̀ọ̀sẹ̀."))


def build(lang: str, src: dict, en: dict) -> dict:
    out = {"lang": lang, "lang_name": src["lang_name"], "version": "0.1.0-draft", "reviewed": False,
           "tts": False, "draft_note": "AI-drafted, NOT reviewed. A native speaker must check every line.",
           "reviewer": {"name": "", "date": "", "role": ""},
           "ui": {}, "crops": {}, "questions": {}, "diagnoses": {}, "steps": {}}
    missing = []
    for sec in ("ui", "crops", "questions"):
        for k in en[sec]:
            if k in src[sec]:
                out[sec][k] = src[sec][k]
            else:
                missing.append(f"{sec}.{k}")
    for k, v in en["diagnoses"].items():
        if k in src["diagnoses"]:
            out["diagnoses"][k] = {"name": src["diagnoses"][k], "audio": v.get("audio", f"d_{k}.mp3")}
        else:
            missing.append(f"diagnoses.{k}")
    for k in en["steps"]:
        if k in src["steps"]:
            out["steps"][k] = {"text": src["steps"][k]}
        else:
            missing.append(f"steps.{k}")
    if missing:
        raise SystemExit(f"{lang}: missing {missing}")
    if "{n}" not in out["ui"]["press_option"] or "{option}" not in out["ui"]["press_option"]:
        raise SystemExit(f"{lang}: press_option must keep {{n}} and {{option}}")
    return out


if __name__ == "__main__":
    en = json.loads((ROOT / "en.json").read_text(encoding="utf-8"))
    for lang, src in T.items():
        (ROOT / f"{lang}.json").write_text(json.dumps(build(lang, src, en), indent=2, ensure_ascii=False), encoding="utf-8")
        print("wrote", lang)
