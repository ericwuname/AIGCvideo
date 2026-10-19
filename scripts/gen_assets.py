#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
资产批量生成器
用法: python gen_assets.py <组名>
组名定义在 GROUPS 里，每组一次出多张候选供挑选
"""
import json, os, sys, time, urllib.request, urllib.error
from concurrent.futures import ThreadPoolExecutor, as_completed

KEY = "cpk-mzkDZfpAidgqI3vMf1dniX6XRxUe9K1onvMQf1gzUGCRqqI9"
BASE = "https://api.agnes-ai.cn/v1"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

NEG_GENERAL = ("不要动漫风，不要游戏CG，不要插画感，不要塑料质感，不要过度磨皮，"
               "不要高饱和，不要棚拍平光，不要文字水印，不要镜像扭曲")
# 龙的负面段（关键：压制西方龙与鳄鱼）
NEG_DRAGON = ("no western dragon, no wings, no bat wings, no crocodile, no alligator, "
              "no lizard, no dinosaur, no t-rex, no fish head, no short snout, no exposed fangs, "
              "not cartoon, not anime, not illustration, not 3d render, not plastic, no text")

# 组名 -> (输出目录, 参考图路径或None, 张数, [prompt...])
GROUPS = {
    # ===== 龙母版候选：不同方向各出一张 =====
    "dragon_master": ("assets/creature", None, None, [
        # A 全身水中穿行（无角=蛟态）
        ("AST-CREATURE-001_master_A",
         "An Eastern dragon, long serpentine body covered in wet golden carp-like scales, "
         "four short powerful clawed legs, horse-like head with flowing whiskers and a long beard, "
         "no horns, sinuous body gliding through dark flood water at night, half submerged, "
         "torrential rain, lighting from a single distant lightning flash, wet scales catching light, "
         "hyper-realistic cinematic photography, epic scale, shot on 35mm film, shallow depth of field"),
        # B 穿云升腾（动态）
        ("AST-CREATURE-001_master_B",
         "An Eastern dragon rising through storm clouds, long sinuous serpentine body spiraling upward, "
         "golden scales glinting, four short clawed legs extended, horse-like head, long flowing whiskers, "
         "no horns, seen from below at a dramatic angle, dark stormy sky, lightning illuminating the clouds from within, "
         "hyper-realistic cinematic photography, epic scale, film grain"),
        # C 头部特写（无角）
        ("AST-CREATURE-001_master_C",
         "Close-up of an Eastern dragon's head, horse-like skull structure, broad blunt snout, "
         "long flowing whiskers, a long beard, golden eyes with vertical slit pupils, "
         "wet golden scales around the face, no horns, no fangs showing, "
         "rain streaming down its face, dark storm background, single cold light source, "
         "hyper-realistic cinematic photography, shallow depth of field, 35mm film grain"),
        # D 脊背破水（局部，最有气势）
         ("AST-CREATURE-001_master_D",
         "An enormous scaled ridge breaking the surface of dark flood water at night, "
         "a long row of wet golden scales with dark edges, blood seeping from cracked scales, "
         "water cascading off the ridge, only the back visible, no head, no tail, "
         "dramatic single lightning flash, torrential rain, "
         "hyper-realistic cinematic photography, epic scale, 35mm film grain"),
        # E 盘曲长躯（侧面剪影）
        ("AST-CREATURE-001_master_E",
         "Silhouette of an Eastern dragon's long serpentine body coiling through storm clouds at night, "
         "backlit by lightning, only the sinuous outline and the glint of scales visible, "
         "four clawed legs faintly visible, no horns, no wings, majestic and terrifying scale, "
         "hyper-realistic cinematic photography, high contrast, film grain"),
        # F 爪与鳞细节
        ("AST-CREATURE-001_master_F",
         "Extreme close-up of an Eastern dragon's claw gripping wet dark rock, "
         "four curved talons, golden scales around the wrist, water running over the scales, "
         "texture of real reptile skin but with golden carp-like scale pattern, "
         "single cold rim light, torrential rain, hyper-realistic macro cinematography, shallow depth of field"),
    ]),

    # ===== 无角蛟（渡劫前状态）——v1 漏了 no horns 导致全长了角 =====
    "jiao_no_horn": ("assets/creature", None, None, [
        ("AST-CREATURE-001_jiao_ridge_v1",
         "An enormous scaled ridge of a giant water serpent breaking the surface of dark flood water at night, "
         "wet dark-golden scales with cracked edges seeping dark blood, water cascading off the ridge, "
         "the head is far away and barely visible, the head is completely smooth with NO horns and NO antlers, "
         "exhausted and wounded, torrential rain, a single lightning flash illuminating the scales, "
         "hyper-realistic cinematic photography, epic scale, 35mm film grain"),
        ("AST-CREATURE-001_jiao_head_v1",
         "The head of a giant wounded water serpent slowly emerging from dark flood water at night, "
         "broad blunt horse-like skull, completely smooth head with NO horns and NO antlers, "
         "long flowing whiskers, mouth closed and NO fangs and NO visible teeth, "
         "eyes half-closed in exhaustion and pain, cracked scales on the jaw seeping blood, "
         "rain streaming down its face, one cold light source from the side, "
         "hyper-realistic cinematic photography, shallow depth of field, 35mm film grain"),
        ("AST-CREATURE-001_jiao_shadow_v1",
         "A very long dark shadow moving beneath murky flood water at night, "
         "only a vast dark silhouette and the raised, bulging water surface visible above it, "
         "immense length suggesting something enormous, no details visible, no head, "
         "torrential rain breaking the surface, cold blue tones, "
         "hyper-realistic cinematic photography, shot from the shore, 35mm film grain"),
    ]),

    # ===== 竖瞳眼睛（剧本镜7：疲惫而平静，禁凶相）=====
    "dragon_eye": ("assets/creature", None, None, [
        ("AST-CREATURE-002_eye_exhausted_v1",
         "Extreme close-up of a giant serpent's eye looking at the camera, "
         "golden iris with a vertical slit pupil, wet dark scaly skin around the eye, "
         "the expression is exhausted and calm and almost gentle, not fierce, not angry, "
         "water droplets on the scales, a single cold light reflection in the pupil, "
         "hyper-realistic macro cinematography, very shallow depth of field, 35mm film grain"),
        ("AST-CREATURE-002_eye_side_v1",
         "Extreme close-up of a giant serpent's eye seen from a slight three-quarter angle, "
         "golden iris, vertical slit pupil, heavy eyelid half lowered out of exhaustion, "
         "wet scales, rain running over the skin, single rim light, "
         "hyper-realistic macro cinematography, shallow depth of field, cinematic"),
    ]),

    # ===== 环境资产 =====
    "env": ("assets/env", None, None, [
        ("AST-ENV-001_village_rain_v1",
         "Wide shot of a small Chinese riverside fishing village at night in torrential rain, "
         "whitewashed walls and dark tiled roofs, wet stone steps leading down into a swollen flooded river, "
         "small wooden boats moored and one drifting loose, a single warm oil lamp glowing in a doorway, "
         "cold blue night tones with that warm accent, heavy rain visible in the air, "
         "hyper-realistic cinematic photography, 35mm film grain, deep focus"),
        ("AST-ENV-002_thunder_sky_v1",
         "A violent storm sky at night above a flooded river, towering cumulonimbus clouds, "
         "several lightning bolts striking down toward the water, cold blue and white light, "
         "no land, no people, just sky and water, immense scale, "
         "hyper-realistic cinematic photography, epic, 35mm film grain"),
        ("AST-ENV-003_dawn_river_v1",
         "Dawn over a flooded river just after a storm, pale cold morning light breaking through "
         "the last receding clouds, calm muddy water reflecting the sky, low mist over the surface, "
         "distant dark treeline, quiet and empty, "
         "hyper-realistic cinematic photography, 35mm film grain, deep focus"),
    ]),

    # ===== 墨龙母版 v3.0（用户否掉金龙：金鳞是帝王祥瑞，刚化龙不该是金色）=====
    # 依据：五色龙五行说——黑龙江属水、掌洪水、"最凶"，契合走蛟语境
    "dragon_black": ("assets/creature", None, None, [
        ("AST-CREATURE-001_black_A",
         "An Eastern dragon rising out of dark flood water at night, long serpentine body, "
         "jet-black scales with a faint cold blue-green iridescence, wet and glistening with muddy water, "
         "four clawed legs, horse-like head with flowing whiskers and a long beard, no wings, "
         "many scales cracked and missing, old lightning scars across the flank, blood seeping, "
         "wild, wounded, menacing, NOT auspicious, NOT decorative, "
         "torrential rain, a single lightning flash, dark desaturated cold tones, "
         "hyper-realistic cinematic photography, 35mm film grain, shallow depth of field"),
        ("AST-CREATURE-001_black_B",
         "An enormous scaled ridge of a black Eastern dragon breaking the surface of dark flood water at night, "
         "jet-black scales edged with cold blue-green iridescence, wet, cracked edges seeping dark blood, "
         "water cascading off the ridge, only the back visible, no head, no tail, "
         "torrential rain, a single lightning flash illuminating the wet scales, "
         "hyper-realistic cinematic photography, epic scale, dark and desaturated, 35mm film grain"),
        ("AST-CREATURE-001_black_C",
         "Silhouette of an Eastern dragon's long serpentine body coiling through violent storm clouds at night, "
         "backlit by lightning, only the sinuous outline and the cold glint of wet black scales visible, "
         "four clawed legs faintly visible, no wings, majestic and terrifying, "
         "hyper-realistic cinematic photography, very dark, high contrast, 35mm film grain"),
        ("AST-CREATURE-001_black_D",
         "Extreme close-up of Eastern dragon scales on a living body, "
         "jet-black scales with cold blue-green iridescence, wet and glistening, "
         "several scales cracked and torn away exposing raw flesh, a scar from a lightning burn, "
         "rain water running over the surface, "
         "hyper-realistic macro cinematography, very shallow depth of field, dark, 35mm film grain"),
        ("AST-CREATURE-001_black_E",
         "Extreme close-up of a black Eastern dragon's claw gripping wet dark rock, "
         "four curved talons, jet-black scales around the wrist with cold blue-green sheen, "
         "water running over the scales, mud and grit, "
         "single cold rim light, torrential rain, hyper-realistic macro cinematography, dark, film grain"),
        ("AST-CREATURE-001_black_F",
         "Close-up of a black Eastern dragon's head emerging from dark water at night, "
         "horse-like skull structure, blunt broad snout, long flowing whiskers, a long beard, "
         "deep amber eyes with vertical slit pupils, exhausted and calm not fierce, "
         "mouth closed with no fangs showing, "
         "jet-black wet scales with cold blue-green sheen, a fresh wound on the jaw, "
         "no wings, torrential rain, single cold light source, "
         "hyper-realistic cinematic photography, shallow depth of field, dark, 35mm film grain"),
    ]),

    # ===== 蛟的再尝试（用户认为可以生成；改用"具体形体描述"而非"dragon + 无角"）=====
    "jiao_attempt": ("assets/creature", None, None, [
        ("AST-CREATURE-001_jiao_v2_a",
         "A colossal aquatic serpent, body as thick as a river barge's hull covered in huge wet slate-grey scales, "
         "four short powerful limbs with hooked claws, seen half-submerged in churning muddy flood water at night, "
         "only a segment of its body visible, no head in frame, "
         "mud and dead branches caught between the scales, wounds seeping blood, "
         "torrential rain, single lightning flash, hyper-realistic cinematic photography, "
         "epic scale, dark desaturated, 35mm film grain"),
        ("AST-CREATURE-001_jiao_v2_b",
         "A giant drowned serpent surfacing in a flooded river at night, "
         "broad blunt reptilian skull with a smooth crown and no horns, "
         "slate-grey scales streaked with mud, eyes half-closed in exhaustion, "
         "no visible fangs, no fins, no fish tail, "
         "long heavy body trailing behind it under the water, "
         "torrential rain, one cold side light, hyper-realistic cinematic photography, dark, 35mm film grain"),
        ("AST-CREATURE-001_jiao_v2_c",
         "A vast dark shape moving beneath muddy flood water at night, "
         "only the enormous raised bulge on the water surface and a vague dark mass beneath it, "
         "faint rings of slate-grey scales catching the light at the crest, "
         "the rest is unreadable darkness under the water, "
         "torrential rain, cold blue tones, shot from a low angle at the shore, "
         "hyper-realistic cinematic photography, 35mm film grain"),
        ("AST-CREATURE-001_jiao_v2_d",
         "Ancient Chinese ink-painting inspired depiction rendered as a real photograph: "
         "a colossal serpent-dragon rising from a stormy river at night, "
         "body like a 汉代画像砖 走龙 silhouette, elongated and low, four short legs, "
         "slate-grey and black scales, wet and heavy, no horns, no wings, no fins, "
         "torrential rain, single lightning flash, "
         "hyper-realistic cinematic photography, dark, desaturated, 35mm film grain"),
    ]),

    # ===== 蛟 v3：基于 jiao_v2_d 的成功方向（长颈蛇形 + 无角 + 脊刺 + 侧影）=====
    "jiao_v3": ("assets/creature", None, None, [
        ("AST-CREATURE-001_jiao_v3_a",
         "A colossal long-necked water serpent rising through a stormy river at night, "
         "completely smooth hornless skull, elongated serpentine neck, "
         "a ridge of bony spines running down its back, slate-grey and black wet scales, "
         "no wings, no fins, no legs visible, low in the water, "
         "side view silhouette against lightning, torrential rain, "
         "hyper-realistic cinematic photography, dark desaturated, 35mm film grain"),
        ("AST-CREATURE-001_jiao_v3_b",
         "A gigantic serpent's body arcing out of churning flood water at night, "
         "only the long middle section visible, heavy slate-grey scales with mud and debris, "
         "a row of bony dorsal spines, water pouring off its back, no head, no tail, "
         "side view, torrential rain, single lightning flash, "
         "hyper-realistic cinematic photography, epic scale, dark, 35mm film grain"),
        ("AST-CREATURE-001_jiao_v3_c",
         "Low angle view from the flooded shore: a vast long-bodied water beast half submerged, "
         "smooth hornless head turned in profile, only the neck and shoulder above water, "
         "slate-grey scaly hide with dorsal spines, exhausted posture, no fangs visible, "
         "torrential rain, one cold rim light, hyper-realistic cinematic photography, "
         "dark desaturated, 35mm film grain"),
        ("AST-CREATURE-001_jiao_v3_d",
         "An ancient colossal serpent coiled in a flooded valley at night, seen from far away for scale, "
         "its long body winding across the water like a low mountain range, "
         "dorsal spines catching the lightning, smooth hornless head at the far end, "
         "no wings, no legs, torrential rain, "
         "hyper-realistic cinematic photography, epic scale, dark, 35mm film grain"),
    ]),

    # ===== 蛟 v5：烛龙启发 —— 无足 / 盘曲 / 兽首 =====
    # 关键推理：只要出现「长身+四足+水」，AI 必落进蛇颈龙/鳄鱼/龟三个模板。
    # 烛龙「人面蛇身」无足（《淮南子》"人面龙身而无足"），去掉足可避开爬行类模板。
    # 另外用户嫌"特别长"，改为盘曲构图，不横向拉成一条虫。
    "jiao_v5": ("assets/creature", None, None, [
        ("AST-CREATURE-001_jiao_v5_coiled_a",
         "An ancient Chinese water serpent called Jiao coiling upward in a flooded river at night, "
         "body coiled in a compact spiral, thick and heavy, NOT thin, NOT stretched out sideways, "
         "the head of a tiger at the top of the coil, feline skull, round ears, blunt muzzle, whiskers, "
         "utterly without legs, no limbs, no fins, no wings, "
         "hide covered in rounded bead-like nodules not fish scales, dark slate-black with cold blue-green sheen, "
         "completely hornless, vertical slit pupils, "
         "torrential rain, single lightning flash, half-submerged, "
         "hyper-realistic cinematic photography, epic scale, dark desaturated, 35mm film grain"),
        ("AST-CREATURE-001_jiao_v5_coiled_b",
         "A colossal hornless water serpent rising in a vertical spiral out of dark flood water at night, "
         "seen from a low angle, the coil filling the frame, immense girth, "
         "a tiger-like head at the summit turned in three-quarter profile, "
         "no legs at all, no arms, no claws, no fins, "
         "bead-textured dark hide wet with rain, "
         "torrential rain, one lightning bolt behind it as a rim light, "
         "hyper-realistic cinematic photography, dramatic, dark, 35mm film grain"),
        ("AST-CREATURE-001_jiao_v5_local",
         "Extreme close-up of a coiled serpent body in muddy flood water at night, "
         "the coil so thick it fills the frame edge to edge, "
         "hide of rounded bead-like nodules, dark slate-black with cold blue-green sheen, "
         "no legs, no head, no tail, just the mass of the coiled body, "
         "water sheeting off it, torrential rain, single cold light, "
         "hyper-realistic macro cinematography, shallow depth of field, dark, 35mm film grain"),
        ("AST-CREATURE-001_jiao_v5_head_coiled",
         "An ancient Chinese water serpent rearing up out of a flooded river at night, "
         "the neck rising in an S curve, a tiger-like head with round ears and blunt muzzle, "
         "mouth closed, no fangs showing, vertical slit pupils, exhausted and calm, "
         "no horns, no legs visible, bead-textured dark hide, "
         "torrential rain, single cold rim light on the face, "
         "hyper-realistic cinematic photography, shallow depth of field, dark desaturated, 35mm film grain"),
    ]),

    # ===== 蛟 v6：盘曲巨躯强化（v5_local 是唯一无拼接感的成功方向）=====
    "jiao_v6": ("assets/creature", None, None, [
        ("AST-CREATURE-001_jiao_v6_arc",
         "A single enormous arc of a coiled serpent body breaking the surface of a flooded river at night, "
         "only one curve of the body visible, both ends disappearing under the muddy water, "
         "hide of rounded bead-like nodules, dark slate-black with cold blue-green sheen, "
         "no legs, no head, no tail, water pouring off the arc, "
         "torrential rain, single lightning flash behind, low angle from the water, "
         "hyper-realistic cinematic photography, epic scale, dark, 35mm film grain"),
        ("AST-CREATURE-001_jiao_v6_underwater",
         "Looking up from beneath murky flood water: the vast dark underside of a coiled serpent body passing overhead, "
         "bead-textured hide, faint cold light filtering through the silty water, "
         "no legs, no head, only the mass of the body, bubbles and suspended mud, "
         "hyper-realistic underwater cinematography, dark, desaturated, 35mm film grain"),
        ("AST-CREATURE-001_jiao_v6_scale",
         "A flooded village street at night seen from a high angle: "
         "an enormous coiled serpent body wound between the half-submerged houses, "
         "the coil spanning the width of the street, bead-textured dark hide, no legs, no head, "
         "torrential rain, a single warm oil lamp still burning in one window for scale, "
         "hyper-realistic cinematic photography, epic scale, dark, 35mm film grain"),
        ("AST-CREATURE-001_jiao_v6_mud",
         "A thick serpent body lying half-buried in wet mud and flood debris at dawn after a storm, "
         "bead-textured dark hide with mud caked into the nodules, still wet, faint cold sheen, "
         "no legs, no head, lifeless and heavy, "
         "pale grey morning light, hyper-realistic cinematic photography, shallow depth of field, 35mm film grain"),
    ]),

    # ===== 蛟 v7：汉画像砖「走龙」造型 + 写实材质 =====
    # 思路转向：不再用动物学描述（必落进鳄鱼/蛇颈龙/巨蛇模板），
    # 改用中国古典造型语言——汉代画像砖走龙的 S 形躯干、小头细颈粗身、四肢外张的行走姿态。
    "jiao_v7": ("assets/creature", None, None, [
        ("AST-CREATURE-001_jiao_v7_turnaround",
         "Creature design turnaround reference sheet, three views side by side: front, side profile, back. "
         "Design based on the Han dynasty stone-relief 'walking dragon' motif: "
         "elongated S-curved body, SMALL head with a short blunt snout, slender neck, thick powerful trunk, "
         "four limbs spread outward in a striding pose, long thin tapering tail, "
         "no wings, no horns, no antlers, "
         "rendered as a living creature with wet dark slate scales and bead-like nodules, "
         "cold blue-green sheen, rain-soaked, "
         "proportions heavy and compact, NOT a thin snake, NOT extremely elongated. "
         "Plain neutral mid-grey background, flat even studio lighting, no shadows, no environment. "
         "Photorealistic creature design, not cartoon, not anime, not illustration, no text"),
        ("AST-CREATURE-001_jiao_v7_stride",
         "A great Chinese water beast in the pose of a Han dynasty stone-relief walking dragon, "
         "S-curved body, small head with short blunt snout, slender neck, thick trunk, "
         "four limbs spread in a striding pose, long thin tail, no wings, no horns, "
         "wet dark slate scales with bead-like nodules, "
         "striding through shallow flood water at night, torrential rain, "
         "single lightning flash from the side, hyper-realistic cinematic photography, "
         "dark desaturated, 35mm film grain"),
        ("AST-CREATURE-001_jiao_v7_rear",
         "A great Chinese water beast rearing up, body coiled in an S shape, "
         "small blunt-snouted head lifted, slender neck, thick trunk, "
         "four limbs spread, long thin tail, no horns, no wings, "
         "wet dark slate scales with a cold sheen, "
         "against a wall of rain and lightning at night, seen from a low angle, "
         "hyper-realistic cinematic photography, epic scale, dark, 35mm film grain"),
        ("AST-CREATURE-001_jiao_v7_head_small",
         "Close-up of the head of a Han-dynasty-style Chinese water dragon: "
         "a SMALL head with a short blunt snout, not a horse head, not a crocodile head, not a tiger head, "
         "no horns, no antlers, no fangs showing, "
         "vertical slit pupils in pale amber eyes, calm and exhausted, "
         "wet dark slate scales with bead-like nodules around the jaw and neck, "
         "rain streaming down, single cold light, "
         "hyper-realistic cinematic photography, shallow depth of field, dark, 35mm film grain"),
    ]),

    # ===== 蛟 v8：走龙造型 + 写实活物质感（v7 造型成立，材质偏模型，这一版强化真实感）=====
    "jiao_v8": ("assets/creature", None, None, [
        ("AST-CREATURE-001_jiao_v8_hero",
         "A great Chinese water beast in the striding pose of a Han dynasty walking dragon, "
         "S-curved body, small blunt-snouted head, slender neck, thick trunk, "
         "four limbs spread mid-stride, long thin tail, no wings, "
         "THIS IS A LIVING ANIMAL, NOT A STATUE, NOT A FIGURINE, NOT A MODEL, "
         "wet real animal skin, dark slate-grey hide with fine scales and bead-like nodules, "
         "mud caked on the belly, an open wound on the shoulder seeping blood, "
         "rain water running off the body, breath steaming in the cold air, "
         "wading through shallow flood water at night, "
         "single lightning flash as rim light, torrential rain, "
         "hyper-realistic cinematic photography, documentary realism, dark desaturated, 35mm film grain"),
        ("AST-CREATURE-001_jiao_v8_roar",
         "A great Chinese water beast rearing up and roaring, body in an S curve, "
         "small blunt-snouted head thrown back, mouth open, slender neck, thick trunk, "
         "four limbs spread wide, long tail whipping, no wings, "
         "LIVING ANIMAL, NOT A STATUE, NOT A MODEL, "
         "wet dark slate hide, mud and blood on the flanks, water flying off the body, "
         "night storm, lightning behind it, torrential rain, seen from below, "
         "hyper-realistic cinematic photography, epic, dark desaturated, 35mm film grain"),
        ("AST-CREATURE-001_jiao_v8_water",
         "A great Chinese water beast half-emerged from a flooded river at night, in the low striding pose of a "
         "Han dynasty walking dragon, S-curved back breaking the surface, "
         "small blunt head low over the water, four limbs in the shallows, long tail trailing, no wings, "
         "LIVING ANIMAL, NOT A STATUE, "
         "wet dark slate hide with mud and weed caught in the scale joints, an open wound on the flank, "
         "torrential rain, one cold light source, water churning around its legs, "
         "hyper-realistic cinematic photography, dark, 35mm film grain"),
        ("AST-CREATURE-001_jiao_v8_turnaround_real",
         "Creature turnaround reference sheet, three views side by side: front, side profile, back. "
         "A great Chinese water beast designed on the Han dynasty walking-dragon motif: "
         "S-curved body, small blunt-snouted head, slender neck, thick trunk, "
         "four limbs spread, long thin tail, no wings, no horns, "
         "rendered as a LIVING WET ANIMAL with real skin, dark slate scales, bead nodules, "
         "mud and scars, NOT a statue, NOT a figurine, NOT plastic, "
         "Plain neutral mid-grey background, flat even studio lighting, no shadows, no environment. "
         "Photorealistic creature design, not cartoon, not illustration, no text"),
    ]),

    # ===== 蛟 v9：终极规格（综合古籍+百科精确描述）=====
    # 依据：身躯数丈且粗壮 / 珍珠般硬鳞 / 前肢宽扁如桨 / 眉间交叉肉块 / 眼凹陷 /
    #      颈白纹 背蓝纹 胸赭色 / 尾尖硬刺 / 黏滑涎液 / 邪恶嗜血（蛟=邪恶，龙=正义）
    "jiao_v9": ("assets/creature", None, None, [
        ("AST-CREATURE-001_jiao_v9_turnaround",
         "Creature design turnaround sheet of an ancient Chinese water beast called JIAO, NOT a dragon. "
         "Three views side by side: front, side, back, identical proportion, feet on the same ground line. "
         "BODY: very thick and heavy serpentine body, like an enormous python but far more massive, "
         "lying LOW with the belly dragging the ground, four SHORT limbs, "
         "the FRONT limbs broad and flat like paddles, the hind limbs stubby; "
         "SKIN: dense small hard scales like packed pearls, slick with slimy saliva, wet and glistening; "
         "HEAD: small feline head like a tiger, slender neck, "
         "a pair of CROSSED FLESHY RIDGES between the eyes, sunken eyes with vertical slit pupils, "
         "no horns or only a single short straight horn, no flowing whiskers, no mane, no beard; "
         "COLOR: white markings on the neck, dark blue markings along the back, ochre chest, dark slate base; "
         "TAIL: long thin snake tail ending in a hard spike; no wings. "
         "This is a repulsive predatory monster, EVIL and bloodthirsty, "
         "NOT majestic, NOT sacred, NOT auspicious. "
         "Plain neutral mid-grey background, flat even lighting, no shadows, no environment. "
         "Photorealistic creature design, not cartoon, not illustration"),
        ("AST-CREATURE-001_jiao_v9_crawl",
         "An ancient Chinese water beast called JIAO crawling low along a flooded riverbank at night, "
         "NOT a dragon, NOT a dinosaur: "
         "a very thick heavy serpentine body dragging its belly in the mud, "
         "four short limbs, the front limbs broad and flat like paddles, "
         "dense pearl-like hard scales slick with slimy saliva, "
         "a small tiger-like head on a slender neck, CROSSED FLESHY RIDGES between the eyes, "
         "sunken eyes with vertical slit pupils, no horns, "
         "white neck markings, dark blue back markings, ochre chest, "
         "long snake tail with a hard spike at the tip, no wings, "
         "EVIL and predatory, hunting, "
         "torrential rain, single cold light, hyper-realistic cinematic photography, dark, 35mm film grain"),
        ("AST-CREATURE-001_jiao_v9_head",
         "Extreme close-up of the head of an ancient Chinese water beast called JIAO, NOT a dragon: "
         "a small feline head like a tiger, slender neck, "
         "a pair of CROSSED FLESHY RIDGES between the eyes, "
         "SUNKEN eyes with vertical slit pupils, cold and malevolent, "
         "no horns, no flowing whiskers, no beard, no mane, "
         "dense pearl-like hard scales slick with slimy wet saliva, "
         "white markings on the neck, mouth closed, no fangs showing, "
         "rain streaming down, single cold light source, "
         "hyper-realistic cinematic photography, shallow depth of field, dark, EVIL atmosphere"),
        ("AST-CREATURE-001_jiao_v9_water",
         "An ancient Chinese water beast called JIAO half submerged in a flooded river at night, "
         "only a long thick section of its body and one paddle-like front limb breaking the surface, "
         "dense pearl-like hard scales wet and glistening with slime, "
         "dark blue markings along the back, white neck markings, "
         "no head visible, no wings, long snake tail trailing with a hard spike, "
         "torrential rain, one cold light, the water churning around it, "
         "hyper-realistic cinematic photography, dark, menacing, 35mm film grain"),
    ]),

    # ===== 蛟 v10：鳞皮头部（修正 v9 的"虎头长毛"）+ 暗黑配色 =====
    # 关键修正：蛟是鳞皮水生动物，头部不能有毛发/虎纹；颜色要去掉橘黄等亮色
    "jiao_v10": ("assets/creature", None, None, [
        ("AST-CREATURE-001_jiao_v10_head",
         "Extreme close-up of the head of an ancient Chinese water beast called JIAO, NOT a dragon, NOT a tiger: "
         "the skull structure is feline but the head is entirely covered in dense pearl-like wet scales, "
         "NO FUR, NO HAIR, NO WHISKERS, NO TIGER STRIPES, no mane, "
         "a pair of CROSSED FLESHY RIDGES between the eyes, "
         "SUNKEN eyes with vertical slit pupils, cold and malevolent, "
         "no horns, mouth slightly open in a snarl, "
         "the whole head slick with slimy wet saliva, water dripping, "
         "colors are DARK AND MURKY: black, dark teal, dried blood brown, NO orange, NO bright yellow, "
         "rain streaming down, single cold hard light from the side, "
         "hyper-realistic cinematic photography, shallow depth of field, EVIL menacing atmosphere"),
        ("AST-CREATURE-001_jiao_v10_crawl_dark",
         "An ancient Chinese water beast called JIAO crawling low through a flooded street at night, "
         "NOT a dragon, NOT a dinosaur, NOT a salamander: "
         "very thick heavy serpentine body dragging its belly in the black water, "
         "four short limbs, the front ones broad and flat like paddles, "
         "dense pearl-like hard scales, slick and slimy, "
         "the head is feline in structure but covered in scales with NO fur and NO tiger stripes, "
         "crossed fleshy ridges between the eyes, sunken eyes with vertical slit pupils, no horns, "
         "DARK MURKY COLORS ONLY: black, dark teal, dried blood, no orange, no bright tones, "
         "EVIL, predatory, stalking, no wings, "
         "torrential rain, one weak cold light, deep shadows, "
         "hyper-realistic cinematic photography, dark, 35mm film grain"),
        ("AST-CREATURE-001_jiao_v10_turnaround_dark",
         "Creature design turnaround sheet of an ancient Chinese water beast called JIAO, NOT a dragon: "
         "front, side, back views side by side, identical proportion, feet on the same ground line. "
         "Very thick heavy serpentine body lying LOW with the belly on the ground, "
         "four short limbs, the front limbs broad and flat like paddles, "
         "dense pearl-like hard scales, slick with slime, "
         "small feline skull structure but the head is fully scaly with NO fur and NO tiger stripes, "
         "crossed fleshy ridges between the eyes, sunken vertical-slit eyes, no horns, no mane, no beard, "
         "DARK MURKY COLORS ONLY: black, dark teal, dried blood brown, ochre underbelly, "
         "long snake tail with a hard spike, no wings, "
         "a repulsive predatory monster, EVIL, NOT majestic, NOT sacred, "
         "Plain neutral mid-grey background, flat even lighting, no shadows. "
         "Photorealistic creature design, not cartoon, not illustration"),
    ]),

    # ===== 蛟 v11：只给局部，永不露全貌 =====
    # 转向理由：连续六轮"完整形态"全部失败（豹子头+鱼鳍+鳄鱼身=拼接怪，可笑不可怕）。
    # 电影手法：大白鲨/异形/克苏鲁都不给全貌。看清了就只剩"设计得丑不丑"。
    "jiao_partial": ("assets/creature", None, None, [
        ("AST-CREATURE-001_partial_limb",
         "Extreme close-up of ONE front limb of an enormous water beast plunging into wet black mud at night, "
         "a broad flat paddle-like limb with hooked claws, dense pearl-like scales slick with slime, "
         "the rest of the body is completely out of frame, only this single limb is visible, "
         "mud squeezing up between the claws, torrential rain, "
         "one cold hard light, hyper-realistic macro cinematography, very shallow depth of field, dark"),
        ("AST-CREATURE-001_partial_tail",
         "Extreme close-up of the tip of an enormous snake-like tail whipping across the surface of black flood water "
         "at night, a hard bony spike at the tip, wet pearl-like scales, a spray of black water flung up, "
         "only the last section of the tail is in frame, the body is out of frame, "
         "single cold light, hyper-realistic high-speed cinematography, dark, 35mm film grain"),
        ("AST-CREATURE-001_partial_shadow",
         "Beneath murky black flood water at night: a very long dark mass passing slowly, "
         "only a vague elongated shape and disturbed silt, "
         "at one point a row of pale pearl-like scales catches a sliver of light and then is gone, "
         "the form is unreadable, no head, no limbs, no clear silhouette, "
         "suspended mud and bubbles, hyper-realistic underwater cinematography, very dark, desaturated"),
        ("AST-CREATURE-001_partial_mouth",
         "Extreme close-up of the lower jaw of an enormous water beast opening just under the surface of black water, "
         "rows of thin curved teeth, pale wet gum, strings of slime between the teeth, "
         "only the mouth is in frame, the rest of the head is out of frame, "
         "single cold light raking across the teeth, torrential rain, "
         "hyper-realistic macro cinematography, shallow depth of field, dark, menacing"),
        ("AST-CREATURE-001_partial_scale_slime",
         "Extreme close-up of a patch of skin of an enormous water creature: "
         "dense small hard scales packed like pearls, slick with thick clear slime, "
         "a few scales missing exposing raw flesh, mud and a bit of weed caught in the joints, "
         "only the skin surface, nothing else in frame, "
         "single cold light, hyper-realistic macro cinematography, shallow depth of field, dark"),
    ]),

    # ===== 蛟 v12：清晰可见的局部 =====
    # 方向修正：partial_shadow 太暗（看不清），不是"局部"。真正的局部是：
    # 观众能清清楚楚看到这一个部位，但永远不能拼成完整形象（毕加索画牛）。
    # 关键：每张只给**一个**身体部位，极其清晰；多张不重不拼。
    "jiao_clear": ("assets/creature", None, None, [
        ("AST-CREATURE-001_clear_claw",
         "Extreme close-up of a single three-toed foot of an enormous water creature pressing into wet black mud at night, "
         "the toes are long curved and clawed, with thin webbing between them, "
         "covered in dense small pearl-like scales slick with clear slime, "
         "the claws leave deep gouges in the mud, water pooling around the foot, "
         "ONLY this single foot is visible, the rest of the body is completely out of frame, "
         "torrential rain, single cold hard light, "
         "hyper-realistic macro cinematography, very shallow depth of field, dark, menacing"),
        ("AST-CREATURE-001_clear_scale_pattern",
         "Extreme close-up of a patch of skin of an enormous water creature: "
         "dense small hard scales packed like pearls, every scale clearly visible, "
         "each scale with subtle dark blue or ochre shading, "
         "a few scales missing exposing raw pink flesh, "
         "a thin trail of clear slime across the surface, "
         "ONLY the skin surface, nothing else in frame, no body outline, no face, no limb, "
         "single cold hard light, hyper-realistic macro cinematography, very shallow depth of field, dark"),
        ("AST-CREATURE-001_clear_eye",
         "Extreme close-up of one eye of an enormous water creature, "
         "the eye is SUNKEN into the scaled skin, vertical slit pupil, amber iris, cold and malevolent, "
         "the surrounding skin is covered in small wet pearl-like scales, NO fur, NO hair, "
         "the rest of the face is out of frame, "
         "single cold light, hyper-realistic macro cinematography, very shallow depth of field, dark"),
        ("AST-CREATURE-001_clear_mouth",
         "Extreme close-up of the lower jaw and teeth of an enormous water creature, "
         "rows of thin curved sharp teeth, pale wet gum, strings of clear slime hanging between the teeth, "
         "a few drops of black water dripping off the teeth, "
         "ONLY the lower jaw and teeth, the rest of the head is out of frame, "
         "single cold hard light raking across the wet teeth, "
         "hyper-realistic macro cinematography, very shallow depth of field, dark, menacing"),
    ]),

    # ===== 蛟 v13：反应镜头 + 痕迹暗示 =====
    # 思路：放弃"画蛟本身"。学《异形》《大白鲨》——只画巨物经过时留下的痕迹，
    # 观众脑补的部分永远比画出来的可怕。
    "jiao_trace": ("assets/creature", None, None, [
        ("AST-CREATURE-001_trace_hair",
         "At the edge of a flooded street at night, a single long black hair lying on the surface of the black water, "
         "a vast unseen thing moving under the water sends out a slow current that pulls the hair along, "
         "the water surface bulges very slightly in a long curve, then stills, "
         "ONLY the hair, the water surface, and the faint bulge are visible, the thing itself is unseen, "
         "torrential rain, a single cold light, hyper-realistic cinematic photography, very dark, shallow depth of field, menacing"),
        ("AST-CREATURE-001_trace_bubble",
         "A flooded village street at night: still black water, then a long slow chain of large bubbles rising to the surface, "
         "a long curving line of bubbles following some unseen path under the water, "
         "the water bulges slightly along the line, then the bubbles burst and it is still, "
         "ONLY the bubbles and the water surface, the thing itself is unseen, "
         "torrential rain, one cold streetlight, hyper-realistic cinematic photography, dark, 35mm film grain, ominous"),
        ("AST-CREATURE-001_trace_reflection",
         "Looking down at a puddle of black flood water at night: in the water is a reflection of something dark, "
         "very long, sliding past overhead, but the actual street above is empty, "
         "only the long dark shape in the reflection is visible, distorted by ripples, "
         "a single weak cold streetlight reflection, hyper-realistic cinematic photography, very dark, ominous, surreal"),
        ("AST-CREATURE-001_trace_push",
         "A small wooden bowl floating in flood water at night, "
         "the bowl is pushed sideways by an unseen current, slowly accelerating, then shoots away as if shoved, "
         "the water surface bulges in a long curve as the current passes, "
         "the small bowl rocks and fills with water, "
         "ONLY the bowl and the water are visible, the unseen thing that pushed it is not, "
         "torrential rain, single cold light, hyper-realistic cinematic photography, dark, 35mm film grain, menacing"),
    ]),

    # ===== 蛟 v14：龙的退化版 =====
    # 关键转向（用户第七次反馈的方向）：蛟 = 龙在化形前还没长成的样子。
    # 不是未知怪物，是同一种生物的幼态/未完成形态。这样：
    # - 龙有强先验，AI 画得出（避开"生物拼装"陷阱）
    # - 化龙是真实视觉转变（"长大了"）
    # - 避开鳄鱼/蛇颈龙/豹子等所有奇怪模板
    "jiao_juvenile": ("assets/creature", None, None, [
        ("AST-CREATURE-001_juvenile_turnaround",
         "Creature turnaround reference sheet of a young, underdeveloped Eastern dragon, "
         "three views side by side: front, side profile, back, identical proportion, feet on the same ground line. "
         "This is a juvenile form, BEFORE it has matured into a great dragon. "
         "A long serpentine body but more slender and less massive than a mature dragon, "
         "four clawed legs but smaller and more slender, "
         "small head on a slender neck, the head is small relative to the body, "
         "the snout is short and beaky, not the long horse-like snout of a mature dragon, "
         "NO ANTLERS, no flowing whiskers, no beard, no mane, no horn, completely hornless, "
         "the scales are smaller and softer looking than a mature dragon's, "
         "darker and more muted coloring: dark teal, blackish green, with a faint cold sheen, NOT golden, "
         "this is a wet, slick, young creature, NOT majestic, NOT sacred, "
         "slim and hungry looking. "
         "Plain neutral mid-grey background, flat even studio lighting, no shadows, no environment. "
         "Photorealistic creature design, real animal skin, not cartoon, not illustration"),
        ("AST-CREATURE-001_juvenile_head",
         "Close-up of a young underdeveloped Eastern dragon's head: "
         "a SMALL head, short beaky snout, slender neck, "
         "no antlers, no flowing whiskers, no beard, no mane, no horn, completely smooth crown, "
         "covered in small dark teal scales, "
         "vertical slit pupils in pale yellow eyes, the eyes look young and hungry, not ancient, not wise, "
         "a wet mouth slightly open showing small sharp teeth, "
         "rain streaming down, single cold light source, "
         "hyper-realistic cinematic photography, shallow depth of field, dark, menacing"),
        ("AST-CREATURE-001_juvenile_body",
         "A young underdeveloped Eastern dragon, slimmer and smaller than a mature dragon, "
         "long slender serpentine body, four slender clawed legs, "
         "small head, no antlers, no whiskers, no beard, no mane, "
         "dark teal and blackish-green scales, small and soft looking, "
         "lying low in shallow flood water at night, "
         "torrential rain, a single cold flash of lightning, "
         "hyper-realistic cinematic photography, dark, 35mm film grain, ominous"),
        ("AST-CREATURE-001_juvenile_vs_mature",
         "Side by side comparison of two Eastern dragons of the same kind, showing two stages of life: "
         "on the LEFT a young underdeveloped juvenile form, slender body, small head, no antlers, no whiskers, "
         "small dark teal scales, slick and wet, hungry looking; "
         "on the RIGHT a mature powerful form, larger and more massive body, prominent antlers, "
         "long flowing whiskers and beard, jet-black scales with cold blue-green iridescence, majestic and threatening. "
         "Same species, two stages, the left one is the form BEFORE the right one. "
         "Plain neutral mid-grey background, flat even studio lighting, no shadows, no environment. "
         "Photorealistic creature design, not cartoon, not illustration, no text"),
    ]),

    # ===== 蛟 v15：juvenile + 邪恶（保留形态，改气质）=====
    # 用户反馈：juvenile 形态对，但太友善/像傻子/像小龙。要邪恶凶狠，不能变成小龙。
    # 改法：保留juvenile的形态描述（蛇身/四足/无角/瘦小），但气质要改——
    #   眼睛冷光凶 / 嘴紧闭露獠牙 / 颜色脏暗带伤 / 鬃毛贴皮像棘刺 / 姿态低伏攻击
    "jiao_evil": ("assets/creature", None, None, [
        ("AST-CREATURE-001_evil_turnaround",
         "Creature turnaround reference sheet of a young, underdeveloped Eastern dragon, "
         "three views side by side: front, side profile, back, identical proportion, feet on the same ground line. "
         "This is a juvenile form BEFORE maturing, but NOT a friendly baby dragon, NOT a pet, NOT cute, NOT cute at all. "
         "A long serpentine body but more slender and less massive than a mature dragon, "
         "four clawed legs, smaller and more slender than an adult's, "
         "small head on a slender neck, short beaky snout, "
         "NO ANTLERS, no flowing whiskers, no beard, no cute fluffy mane, only short bristling spines along the spine, "
         "the mouth is closed tight, corners of the mouth pulled down, baring sharp teeth, NOT smiling, a snarl, "
         "small dark teal and blackish scales, but DIRTY, with old scars, a few scales missing exposing raw flesh, "
         "slim and tense, predator body language, "
         "NOT majestic, NOT sacred, NOT curious, NOT baby-like, a wild and dangerous creature, evil and malevolent, "
         "Plain neutral mid-grey background, flat even studio lighting, no shadows, no environment. "
         "Photorealistic creature design, real animal skin, not cartoon, not illustration, not cute"),
        ("AST-CREATURE-001_evil_head",
         "Close-up of a young underdeveloped Eastern dragon's head, NOT cute, NOT baby, a predator: "
         "small head, short beaky snout, slender neck, "
         "no antlers, no whiskers, no beard, no cute mane, only bristling spines, "
         "covered in small dark teal scales, DIRTY, with scars and dried blood, "
         "the mouth is closed tight, a snarl, baring sharp yellowed teeth, "
         "EYES: cold, malevolent, vertical slit pupils, pale yellow iris, a predatory gaze, NOT curious, "
         "the eye is not round and bright, it is narrow and menacing, "
         "rain streaming down, single cold hard light, "
         "hyper-realistic cinematic photography, shallow depth of field, dark, EVIL"),
        ("AST-CREATURE-001_evil_strike",
         "A young underdeveloped Eastern dragon in a low predatory crouch, "
         "ready to strike, slimmer and smaller than a mature dragon, "
         "long serpentine body low to the ground, four slender clawed legs coiled, "
         "small head lowered, mouth closed baring teeth, "
         "no antlers, no whiskers, no beard, no mane, only bristling spines, "
         "dark teal and blackish scales, dirty, with scars and dried blood, "
         "a wild and dangerous predator, NOT a friendly creature, NOT a baby, "
         "rain-soaked black mud at night, a single cold flash of lightning, "
         "hyper-realistic cinematic photography, dark, 35mm film grain, menacing"),
        ("AST-CREATURE-001_evil_vs_mature",
         "Side by side comparison of two Eastern dragons of the same kind, two stages of life: "
         "on the LEFT a young underdeveloped juvenile form, slender body, small head, no antlers, no whiskers, "
         "no mane, dark teal and blackish scales DIRTY with scars and dried blood, "
         "low predatory crouch, mouth closed baring teeth, cold malevolent eyes, a wild dangerous predator, NOT cute, NOT a baby; "
         "on the RIGHT a mature powerful form, larger and more massive body, prominent antlers, "
         "long flowing whiskers and beard, jet-black scales with cold blue-green iridescence, majestic and threatening. "
         "Same species, two stages, the left one is the form BEFORE the right one. "
         "Plain neutral mid-grey background, flat even studio lighting, no shadows, no environment. "
         "Photorealistic creature design, not cartoon, not illustration, no text"),
    ]),

    # ===== 蛟 v16：张嘴露牙+暗黑+血（最狠版）=====
    # 目标：去除"小龙"感的最后残余
    "jiao_vicious": ("assets/creature", None, None, [
        ("AST-CREATURE-001_vicious_attack",
         "A young underdeveloped Eastern dragon in a vicious predatory attack pose, "
         "long slender serpentine body low to the ground, four clawed legs coiled to spring, "
         "small head thrust forward, MOUTH WIDE OPEN baring rows of yellowed sharp teeth, "
         "hissing, blood on the teeth and lips, "
         "no antlers, no whiskers, no beard, only bristling spines along the spine, "
         "scales are dark, almost black, with the barest cold teal sheen, not bright, NOT healthy looking, "
         "old scars along the flank, a few scales missing exposing raw flesh, blood on the wounds, "
         "slim, tense, predatory, hungry, a vicious young predator, NOT a friendly baby, NOT a pet, "
         "rain-soaked black mud at night, a single cold flash of lightning, "
         "hyper-realistic cinematic photography, dark, 35mm film grain, menacing, evil"),
        ("AST-CREATURE-001_vicious_hiss",
         "Close-up of a young underdeveloped Eastern dragon hissing, head thrust forward: "
         "small head, short beaky snout, "
         "MOUTH WIDE OPEN showing long sharp teeth, throat muscles straining, "
         "blood at the corners of the mouth, strings of drool, "
         "no antlers, no whiskers, no beard, no mane, only bristling spines, "
         "dark almost black scales with the barest cold teal sheen, scars, "
         "EYES: narrow, malevolent, vertical slit pupils, NOT round, NOT curious, predatory gaze, "
         "a vicious young predator, NOT a friendly creature, NOT a cute creature, evil, "
         "rain streaming down, single cold hard light, "
         "hyper-realistic cinematic photography, very shallow depth of field, dark, menacing"),
    ]),

    # ===== 蛟 v17：蛇一样贴地+粗壮+短腿 =====
    # 用户反馈：头部 v16 可以，身体要改。
    # 关键：像大蟒蛇一样贴地（sprawling belly-dragging），腿非常短（sprawled posture），
    #      体型粗壮肌肉（NOT slender, NOT scrawny）。
    "jiao_snakebody": ("assets/creature", None, None, [
        ("AST-CREATURE-001_snakebody_crawl",
         "A young underdeveloped Eastern dragon lying LOW on the ground like a giant python, "
         "heavy thick muscular serpentine body, NOT slender, NOT scrawny, broad and powerful, "
         "dragging its belly in the wet black mud, "
         "four VERY SHORT legs that barely lift the body, almost stubby, sprawled out to the sides, "
         "a predator's sprawled stalking posture, like a komodo dragon or a giant monitor lizard, "
         "small head on a slender neck, "
         "no antlers, no whiskers, no beard, no mane, only short bristling spines along the spine, "
         "dark almost black scales with the barest cold teal sheen, "
         "mouth closed, teeth bared, malevolent narrow eyes, "
         "vicious, hungry, NOT a friendly baby, NOT a pet, NOT cute, "
         "rain-soaked black mud at night, a single cold flash of lightning, "
         "hyper-realistic cinematic photography, dark, 35mm film grain, menacing"),
        ("AST-CREATURE-001_snakebody_water",
         "A young underdeveloped Eastern dragon with a heavy thick serpentine body, "
         "low and sprawled like a giant python, "
         "wading through shallow flood water at night, body half submerged, "
         "four very short legs splayed out, the water churning around its bulk, "
         "the bulk is broad and muscular, NOT slender, NOT scrawny, "
         "small head lifted slightly, malevolent narrow eyes, mouth closed, teeth bared, "
         "no antlers, no whiskers, no beard, no mane, only bristling spines, "
         "dark almost black scales, "
         "torrential rain, one cold light, "
         "hyper-realistic cinematic photography, dark, 35mm film grain, menacing, evil"),
        ("AST-CREATURE-001_snakebody_coiled",
         "A young underdeveloped Eastern dragon with a heavy thick muscular body, "
         "coiled in a tight S-shape on the wet black mud at night, "
         "like a giant python preparing to strike, "
         "the body is broad and powerful, NOT slender, NOT scrawny, "
         "four very short legs splayed out against the mud, "
         "head thrust forward, mouth OPEN baring yellowed teeth, "
         "no antlers, no whiskers, no beard, no mane, only bristling spines, "
         "dark almost black scales with old scars, "
         "a vicious predator, NOT a baby, NOT a pet, "
         "torrential rain, a single cold flash of lightning, "
         "hyper-realistic cinematic photography, dark, 35mm film grain, menacing, evil"),
        ("AST-CREATURE-001_snakebody_head_ok",
         "Three-quarter view of a young underdeveloped Eastern dragon with a heavy thick serpentine body, "
         "lying low and sprawled like a giant python, "
         "muscular and powerful, NOT slender, "
         "four very short legs splayed out, "
         "the head is the same small cold predatory head as before, "
         "narrow malevolent eyes, mouth open baring teeth, "
         "no antlers, no whiskers, no beard, no mane, only bristling spines, "
         "dark almost black scales, scars, "
         "vicious, hungry, NOT a friendly baby, NOT a pet, NOT cute, evil, "
         "rain-soaked black mud at night, a single cold light, "
         "hyper-realistic cinematic photography, dark, 35mm film grain, menacing"),
    ]),

    # ===== 蛟 v18：定稿合影 turnaround + 成片镜头（image-to-image based on v17 coiled）=====
    # 用户确认 v17 snakebody_coiled 方向对。这是终稿姿势参考。
    "jiao_film": ("assets/creature", "https://cos-platform-outputs.agnes-ai.cn/images/t2i/task_TSLnbJoaVyXrpbfx0IaeYQYnOxQuk39F/output_6e00ff8ba03949028e336eba1048f904.png", None, [
        ("AST-CREATURE-001_film_turnaround_final",
         "Side-by-side reference sheet of the FINAL young underdeveloped Eastern dragon, "
         "two views of the same creature: "
         "on the LEFT, a three-quarter body view of a heavy thick muscular serpentine body lying low and sprawled "
         "like a giant python, four very short legs splayed out, broad and powerful, NOT slender, "
         "dark almost black scales with the barest cold teal sheen, bristling spines, scars, "
         "vicious predator posture, NOT a baby, NOT a pet, NOT cute, evil, "
         "rain-soaked black mud at night, a single cold flash of lightning; "
         "on the RIGHT, close-up of the SAME creature's HEAD: small cold predatory head, "
         "mouth OPEN baring yellowed sharp teeth, narrow malevolent eyes with vertical slit pupils, "
         "bristling spines, no antlers, no whiskers, no beard, no mane, "
         "dark almost black scales, scars, "
         "Same creature, body and head views, "
         "Plain neutral mid-grey background, flat even studio lighting, no shadows, no environment. "
         "Photorealistic creature design, not cartoon, not illustration, no text"),
        ("AST-CREATURE-001_film_break_water",
         "A young underdeveloped Eastern dragon with a heavy thick muscular serpentine body, "
         "lying low and sprawled like a giant python, "
         "bursting up through the surface of black flood water at night, "
         "water cascading off its bulk, four very short legs splayed, "
         "small head thrust forward, mouth open baring teeth, "
         "dark almost black scales with cold teal sheen, scars, "
         "vicious predator, NOT a baby, NOT cute, evil, "
         "torrential rain, a single cold flash of lightning, "
         "hyper-realistic cinematic photography, dark, 35mm film grain, menacing, epic"),
        ("AST-CREATURE-001_film_lightning",
         "A young underdeveloped Eastern dragon with a heavy thick muscular serpentine body, "
         "lying low and sprawled like a giant python in wet black mud at night, "
         "illuminated by a single massive flash of lightning, "
         "the light rakes across its dark scales, every scar and bristling spine visible, "
         "small head raised, mouth open baring teeth, "
         "four very short legs splayed, "
         "vicious predator, NOT a baby, NOT cute, evil, "
         "torrential rain in the dark, "
         "hyper-realistic cinematic photography, very dark, 35mm film grain, menacing, epic"),
        ("AST-CREATURE-001_film_silhouette",
         "A young underdeveloped Eastern dragon with a heavy thick muscular serpentine body, "
         "lying low and sprawled like a giant python, "
         "seen as a dark silhouette against a single bolt of lightning in the rainy night sky, "
         "the shape clearly reads as a heavy thick low-slung serpentine body with a small head thrust up, "
         "very short legs splayed, "
         "bristling spines along the spine, "
         "vicious predator, NOT a baby, NOT cute, evil, "
         "hyper-realistic cinematic photography, very dark, 35mm film grain, dramatic, epic"),
        ("AST-CREATURE-001_film_headonly",
         "Just the head of a young underdeveloped Eastern dragon, "
         "low and near the surface of black flood water at night, "
         "the rest of the body is fully submerged and out of frame, "
         "small head, short beaky snout, narrow malevolent eyes with vertical slit pupils, "
         "mouth slightly open baring yellowed teeth, "
         "bristling spines, no antlers, no whiskers, no beard, no mane, "
         "dark almost black scales, scars, "
         "vicious predator, NOT a baby, NOT cute, evil, "
         "torrential rain, a single cold light, "
         "hyper-realistic cinematic photography, shallow depth of field, dark, menacing"),
    ]),

    # ===== 蛟 v19：终极定稿（v17 身体 + v15 头部 + 强制无角）=====
    # 关键问题：v18 用 v17 coiled 做参考时，coiled 里的"小角根"被 I2I 放大成两只大角。
    # 解法：用 v15 evil_turnaround（明确无角的"juvenile 龙"）做参考，
    #      prompt 强制"ABSOLUTELY NO HORNS, NO ANTLERS, NO PROTRUSIONS, completely smooth crown"。
    "jiao_final": ("assets/creature", "https://cos-platform-outputs.agnes-ai.cn/images/t2i/task_naTtFsNaEUUbzhCsVfn3vecY2hLh5ozC/output_154d93ad41774511920bd5efa58b79f0.png", None, [
        ("AST-CREATURE-001_final_turnaround",
         "Creature design turnaround reference sheet of a young underdeveloped Eastern dragon, "
         "three views side by side: front, side profile, back, identical proportion. "
         "A long thick muscular serpentine body, heavy and powerful, NOT slender, NOT scrawny, "
         "lying LOW on the ground like a giant python, dragging its belly, "
         "four VERY SHORT legs splayed out to the sides, almost stubby, "
         "small head on a slender neck, "
         "ABSOLUTELY NO HORNS, NO ANTLERS, NO PROTRUSIONS, NO BUMPS on the crown, completely smooth flat head, "
         "no flowing whiskers, no beard, no mane, "
         "ONLY short bristling spines along the spine, not on the head, "
         "dark almost black scales with the barest cold teal sheen, "
         "mouth closed baring teeth, narrow malevolent eyes, "
         "vicious predator, NOT a baby, NOT a pet, NOT cute, evil, "
         "Plain neutral mid-grey background, flat even studio lighting, no shadows, no environment. "
         "Photorealistic creature design, not cartoon, not illustration"),
        ("AST-CREATURE-001_final_break_water",
         "A young underdeveloped Eastern dragon with a heavy thick muscular serpentine body, "
         "lying low and sprawled like a giant python, "
         "bursting up through the surface of black flood water at night, "
         "water cascading off its bulk, four very short legs splayed, "
         "small head thrust forward, mouth open baring teeth, "
         "ABSOLUTELY NO HORNS, NO ANTLERS, NO PROTRUSIONS on the crown, completely smooth, "
         "dark almost black scales with cold teal sheen, scars, "
         "vicious predator, NOT a baby, NOT cute, evil, "
         "torrential rain, a single cold flash of lightning, "
         "hyper-realistic cinematic photography, dark, 35mm film grain, menacing, epic"),
        ("AST-CREATURE-001_final_lightning",
         "A young underdeveloped Eastern dragon with a heavy thick muscular serpentine body, "
         "lying low and sprawled like a giant python in wet black mud at night, "
         "illuminated by a single massive flash of lightning, "
         "the light rakes across its dark scales, every scar visible, "
         "small head raised, mouth open baring teeth, "
         "ABSOLUTELY NO HORNS, NO ANTLERS, NO PROTRUSIONS, completely smooth crown, "
         "four very short legs splayed, "
         "vicious predator, evil, "
         "torrential rain in the dark, "
         "hyper-realistic cinematic photography, very dark, 35mm film grain, menacing, epic"),
        ("AST-CREATURE-001_final_headonly",
         "Just the head of a young underdeveloped Eastern dragon, "
         "low and near the surface of black flood water at night, "
         "the rest of the body fully submerged out of frame, "
         "small head, short beaky snout, "
         "ABSOLUTELY NO HORNS, NO ANTLERS, NO PROTRUSIONS, completely smooth crown, "
         "narrow malevolent eyes with vertical slit pupils, mouth open baring yellowed teeth, "
         "bristling spines ONLY along the spine, not on the head, "
         "dark almost black scales, scars, "
         "vicious predator, NOT a baby, NOT cute, evil, "
         "torrential rain, a single cold light, "
         "hyper-realistic cinematic photography, shallow depth of field, dark, menacing"),
        ("AST-CREATURE-001_final_closeup",
         "Close-up of the head of a young underdeveloped Eastern dragon at night, "
         "ABSOLUTELY NO HORNS, NO ANTLERS, NO PROTRUSIONS on the crown, completely smooth, "
         "small head, short beaky snout, narrow malevolent eyes with vertical slit pupils, "
         "mouth open baring yellowed teeth, "
         "bristling spines ONLY along the spine, not on the head, "
         "dark almost black scales with cold teal sheen, scars, "
         "vicious predator, evil, "
         "torrential rain, a single cold light, "
         "hyper-realistic cinematic photography, very shallow depth of field, dark, menacing"),
    ]),

    # ===== 蛟 v20：终极定稿 v2（v17 身体 + 强无角）=====
    # v19 用 v15 evil 做参考，evolved 出"立姿长腿"。v20 用 v17 snakebody_water 做参考（最贴地+短腿），
    # prompt 强写"无角+不站立+短腿"三条。融合两个版本优点。
    "jiao_film_v2": ("assets/creature", "https://cos-platform-outputs.agnes-ai.cn/images/t2i/task_1UKLrEZ0CE6Hm5tnO1jfIdEcuVP5mtML/output_d318d283a8bb47dfab1e4fd042302d13.png", None, [
        ("AST-CREATURE-001_film2_turnaround",
         "Creature design turnaround reference sheet, three views side by side: front, side, back. "
         "Heavy thick muscular serpentine body, broad and powerful, NOT slender, NOT scrawny, "
         "lying LOW on the ground, belly dragging, sprawling, like a giant python. "
         "Four VERY SHORT legs splayed out to the sides, almost stubby, NOT a tall standing posture. "
         "Small head on a short neck, short beaky snout. "
         "ABSOLUTELY NO HORNS, NO ANTLERS, NO PROTRUSIONS, NO BUMPS on the crown, completely smooth flat head. "
         "NO flowing whiskers, NO beard, NO mane, ONLY short bristling spines along the spine, NOT on the head. "
         "Mouth closed baring teeth, narrow malevolent eyes with vertical slit pupils. "
         "Dark almost black scales with the barest cold teal sheen, scars. "
         "Vicious predator, NOT a baby, NOT a pet, NOT cute, NOT friendly, NOT a juvenile in a cute way, "
         "a young predator, evil. "
         "Plain neutral mid-grey background, flat even studio lighting, no shadows, no environment. "
         "Photorealistic creature design, not cartoon, not illustration"),
        ("AST-CREATURE-001_film2_break_water",
         "A heavy thick muscular serpentine body of a young predator dragon, lying LOW on the ground like a giant python, "
         "bursting up through the surface of black flood water at night, "
         "water cascading off its bulk, four very short legs splayed out, "
         "small head thrust forward, mouth open baring teeth, "
         "ABSOLUTELY NO HORNS, NO ANTLERS, NO PROTRUSIONS on the crown, completely smooth, "
         "dark almost black scales with cold teal sheen, scars, "
         "vicious predator, NOT a baby, NOT cute, evil, "
         "torrential rain, a single cold flash of lightning, "
         "hyper-realistic cinematic photography, dark, 35mm film grain, menacing, epic"),
        ("AST-CREATURE-001_film2_lightning",
         "A young predator dragon with a heavy thick muscular serpentine body, "
         "lying low and sprawled like a giant python in wet black mud at night, "
         "illuminated by a single massive flash of lightning, "
         "the light rakes across its dark scales, every scar visible, "
         "small head raised, mouth open baring teeth, "
         "ABSOLUTELY NO HORNS, NO ANTLERS, NO PROTRUSIONS, completely smooth crown, "
         "four very short legs splayed, "
         "vicious predator, evil, "
         "torrential rain in the dark, "
         "hyper-realistic cinematic photography, very dark, 35mm film grain, menacing, epic"),
        ("AST-CREATURE-001_film2_silhouette",
         "A young predator dragon with a heavy thick muscular serpentine body, "
         "lying low and sprawled like a giant python, "
         "seen as a dark silhouette against a single bolt of lightning in the rainy night sky, "
         "the shape clearly reads as a heavy thick low-slung serpentine body with a small head thrust up, "
         "very short legs splayed, NO visible horns or antlers, completely smooth head profile, "
         "bristling spines along the spine, "
         "vicious predator, NOT a baby, NOT cute, evil, "
         "hyper-realistic cinematic photography, very dark, 35mm film grain, dramatic, epic"),
        ("AST-CREATURE-001_film2_headonly",
         "Just the head of a young predator dragon, "
         "low and near the surface of black flood water at night, "
         "the rest of the body is fully submerged and out of frame, "
         "small head, short beaky snout, "
         "ABSOLUTELY NO HORNS, NO ANTLERS, NO PROTRUSIONS, completely smooth crown, "
         "narrow malevolent eyes with vertical slit pupils, mouth open baring yellowed teeth, "
         "bristling spines ONLY along the spine, not on the head, "
         "dark almost black scales, scars, "
         "vicious predator, NOT a baby, NOT cute, evil, "
         "torrential rain, a single cold light, "
         "hyper-realistic cinematic photography, shallow depth of field, dark, menacing"),
    ]),

    # ===== 墨龙三视图（用户认可墨色方向，补正式 turnaround）=====
    "dragon_black_turnaround": ("assets/creature", None, None, [
        ("AST-CREATURE-001_black_turnaround_v1",
         "Creature turnaround reference sheet of an Eastern dragon, three views side by side: "
         "front, side profile, and back. All three identical in proportion, feet aligned on the ground line. "
         "Long serpentine body, four clawed legs, horse-like head with flowing whiskers and a long beard, "
         "a pair of deer-like antlers, no wings, "
         "hide of jet-black scales with cold blue-green iridescence, some scales cracked and scarred, "
         "wild and menacing, NOT auspicious, NOT decorative, NOT golden, no gold anywhere. "
         "Plain neutral mid-grey background, flat even studio lighting, no shadows, no environment. "
         "Photorealistic creature design, real animal skin texture, "
         "not cartoon, not anime, not illustration, not 3d render, no text"),
    ]),
}


def api_gen(prompt, size="2K", ratio="16:9", ref=None):
    body = {"model": "agnes-image-2.5-flash", "prompt": prompt, "size": size, "ratio": ratio,
            "extra_body": {"response_format": "url"}}
    if ref:
        body["extra_body"]["image"] = [ref] if isinstance(ref, str) else ref
    data = json.dumps(body, ensure_ascii=False).encode("utf-8")
    last = None
    for attempt in range(4):
        try:
            req = urllib.request.Request(BASE + "/images/generations", data=data,
                headers={"Authorization": "Bearer " + KEY, "Content-Type": "application/json"})
            t0 = time.time()
            with urllib.request.urlopen(req, timeout=300) as r:
                d = json.loads(r.read().decode("utf-8"))
            if "data" not in d:
                raise RuntimeError(str(d)[:200])
            return d["data"][0]["url"], time.time() - t0
        except Exception as e:
            last = e
            print(f"    重试{attempt+1}: {e}")
            time.sleep(15 * (attempt + 1))
    raise RuntimeError(f"失败: {last}")


def download(url, path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with urllib.request.urlopen(url, timeout=180) as r, open(path, "wb") as f:
        f.write(r.read())


def main():
    if len(sys.argv) < 2 or sys.argv[1] not in GROUPS:
        print("可用组:", list(GROUPS)); return
    name = sys.argv[1]
    outdir, ref, _, items = GROUPS[name]
    outdir = os.path.join(ROOT, outdir)
    os.makedirs(outdir, exist_ok=True)

    print(f"=== 生成组 {name}：{len(items)} 张 → {outdir} ===")
    urls_file = os.path.join(outdir, f"_{name}_urls.json")
    urls = json.load(open(urls_file, encoding="utf-8")) if os.path.exists(urls_file) else {}

    def work(item):
        fname, p = item
        if fname in urls:
            print(f"  {fname} 已存在，跳过"); return fname, urls[fname]
        full = p + "。" + NEG_GENERAL
        if "CREATURE" in fname:
            full += "。" + NEG_DRAGON
        # 蛟态（渡劫前）必须无角——v1 漏了这条，导致 6 张候选全长了角
        if "jiao" in fname:
            full += "。no horns, no antlers, smooth head, no crown"
        # 墨龙：压掉所有"金/华丽/祥瑞"倾向（用户否掉金龙）
        if "black" in fname:
            full += ("。no gold, no golden scales, no shiny metal, no ornament, no decorative pattern, "
                     "no auspicious feeling, not shiny, not bright")
        try:
            u, dt = api_gen(full, ref=ref)
            download(u, os.path.join(outdir, fname + ".png"))
            print(f"  ✓ {fname}  {dt:.1f}s")
            return fname, u
        except Exception as e:
            print(f"  ✗ {fname}: {e}")
            return fname, None

    with ThreadPoolExecutor(max_workers=3) as ex:
        for f in as_completed([ex.submit(work, it) for it in items]):
            fn, u = f.result()
            if u:
                urls[fn] = u
                json.dump(urls, open(urls_file, "w"), ensure_ascii=False, indent=2)
    print(f"\n完成 {len(urls)}/{len(items)}")


if __name__ == "__main__":
    main()
