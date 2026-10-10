# 音效與背景素材來源

素材檔不進版控，只記錄來源。換電腦或重新 clone 後，照下表下載，存成「存檔名稱」放在 `assets/`。
腳本裡的名稱與音量設定在 `generate_episode.py` 的 `SOUNDS`。

**只用 CC0 或公有領域（Public domain）的素材**，不必標示作者也能商用、上架 podcast。新增素材時，先確認頁面上的授權，再補進這張表。

| 腳本名稱 | 存檔名稱 | 授權 | 作者 | 原始頁面 | 備註 |
|---|---|---|---|---|---|
| 開場鈴 | `windchimes.ogg` | Public domain | Esc861 | [Wikimedia Commons](https://commons.wikimedia.org/wiki/File:Windchimes.ogg) | 5.4 秒風鈴 |
| 搖籃曲 | `chopin_prelude_op28_13.mp3` | CC0 | Musopen《The Complete Chopin Collection》 | [Internet Archive：musopen-chopin](https://archive.org/details/musopen-chopin)（檔名 `Prelude Op. 28 no. 13.mp3`） | 蕭邦〈前奏曲〉Op.28 No.13，鋼琴，2:46。節目招牌，開場與結尾儀式用。Musopen 網站擋程式存取，從 Internet Archive 的官方備份下載 |
| 放鬆音樂 | `wandering.wav` | CC0 | Andrewkn | [Freesound #455855](https://freesound.org/people/Andrewkn/sounds/455855/) | 〈Wandering〉，柔和鋼琴加長音墊，4:49。放鬆引導段（吸氣吐氣）用。**Freesound 需登入才能下載** |
| 夜晚蟲鳴 | `night_crickets.wav` | CC0 | Defelozedd94 | [Freesound #522298](https://freesound.org/people/Defelozedd94/sounds/522298/) | 夏夜花園蟲鳴，2:49。**Freesound 需登入才能下載** |
| 河水 | `river_flowing.wav` | CC0 | Tom_Kaszuba | [Freesound #660265](https://freesound.org/people/Tom_Kaszuba/sounds/660265/) | 小河流水，1:07（48kHz/24-bit）。分析過沒有鳥叫等突發聲，音量很平穩。**Freesound 需登入才能下載** |
| 夜晚蟲鳴慢 | `night_crickets_slow.wav` | CC0 | Defelozedd94 | 由 `night_crickets.wav` 自製（見下方） | 放慢到 0.7 倍，4:01。助眠尾段用（ep04 起） |
| 河水慢 | `river_flowing_slow.wav` | CC0 | Tom_Kaszuba | 由 `river_flowing.wav` 自製（見下方） | 放慢到 0.7 倍，1:36。助眠尾段用（ep04 起） |
| 貓頭鷹 | `scops_owl.ogg` | Public domain | Raghu | [Wikimedia Commons](https://commons.wikimedia.org/wiki/File:Otus_sunia.ogg) | 東方角鴞的輕聲鳴叫，10 秒 |
| 輕風 | `wind_gentle.wav` | CC0 | kyles | [Freesound #454360](https://freesound.org/people/kyles/sounds/454360/) | wind light calm soft breeze，1:16。ep10 起用（第 19、23 集也會用）。目前用 Freesound 試聽版（mp3 128kbps）轉 wav，之後可換原檔；換檔不影響 TTS 快取，--offline 重新組裝即可。**Freesound 需登入才能下載原檔** |
| 落葉 | `leaves_rustle.wav` | CC0 | Borgory | [Freesound #751473](https://freesound.org/people/Borgory/sounds/751473/) | Soft Wind in the Trees - Leaves rustle，2:27。ep10 用。`screen_audio.py` 在 42.7、103–105 秒有幾個低頻（30–150 Hz）的風壓起伏，不是鳥叫或碰撞聲。目前用 Freesound 試聽版（mp3 128kbps）轉 wav，之後可換原檔；換檔不影響 TTS 快取，--offline 重新組裝即可。**Freesound 需登入才能下載原檔** |
| 小雨 | `rain_light.wav` | CC0 | felix.blume | [Freesound #512334](https://freesound.org/people/felix.blume/sounds/512334/) | Light rain in a field of bananas trees（墨西哥 Veracruz），原長 10 分鐘，取 190–490 秒共 5 分鐘：`screen_audio.py` 在 134.3 秒有一個 +20.5 dB、音高很強的聲音（像鳥叫），這段之後幾乎沒有突發聲。錄音描述是雨落在香蕉葉上（還沒試聽）。ep11 用。目前用 Freesound 試聽版（mp3 128kbps）轉 wav，之後可換原檔（同樣取 190–490 秒）；換檔不影響 TTS 快取，--offline 重新組裝即可。**Freesound 需登入才能下載原檔** |

## 放慢的環境音（自製，不進版控）

助眠尾段用比較慢、比較安靜的蟲鳴和流水。下載原檔後，在 `assets/` 裡用 ffmpeg 產生：

```
ffmpeg -i night_crickets.wav -af atempo=0.7 -c:a pcm_s16le night_crickets_slow.wav
ffmpeg -i river_flowing.wav -af atempo=0.7 -c:a pcm_s24le river_flowing_slow.wav
```

使用者比較過這些版本的 60 秒試聽檔（響度都對齊到 −30 LUFS），最後選了 atempo：
- `asetrate` 0.75 倍與 0.6 倍：放慢，音高也跟著變低
- `rubberband` 0.7 倍：放慢，音高不變
- `atempo` 0.7 倍：放慢，音高不變

## 旁白的呼吸聲（自製，進版控）

`narrator_inhale_1.wav`、`narrator_inhale_2.wav`、`narrator_exhale.wav`（腳本名稱「吸氣1」「吸氣2」「吐氣」）是從 ep02 旁白的配音切出來、再拉長的，聲音是 Gemini TTS 生成的旁白本人。這些檔案沒辦法重新下載，所以例外放進版控。

| 檔案 | 來源 | 處理 |
|---|---|---|
| `narrator_inhale_1.wav` | ep02 旁白批次音檔 `build/segments/batch_99d0608de5bf6714.wav` 的 23.33–24.30 秒（「慢慢吸一口氣」之後的吸氣，0.97 秒） | 拉長到約 3 秒；淡入 0.5 秒、淡出 0.8 秒 |
| `narrator_inhale_2.wav` | 同一檔的 37.13–37.88 秒（「再一次。吸氣」之後，0.75 秒） | 拉長到約 3 秒；淡入 0.5 秒、淡出 0.8 秒 |
| `narrator_exhale.wav` | ep02 旁白「再慢慢地，`<exhales>` 吐出來」裡的吐氣聲（0.85 秒） | 拉長 4 倍（約 3.4 秒）；淡入 0.15 秒、淡出 1.5 秒 |

拉長用 ffmpeg：`rubberband=tempo=<1/倍數>:pitch=1:transients=smooth:window=long:formant=preserved`。

切句時，句尾的吸氣只留下前 0.4 秒（被當成句間靜音切掉），所以腳本用 `[音效 吸氣1 剪 自動]` 先剪掉那半口氣（程式自動量長度），再接上完整拉長的版本。

## ep03 的哈欠（自製，進版控）

ep03 第二次生成（2026-10-05）的 `<yawn>` 都只念成一小口氣，聽起來像吸氣或吐氣。舊版 ep03（2026-10-02 生成，`build/ep03_yawn.m4a`，16kHz 單聲道 AAC 15 kbps）的哈欠配得很好，所以把舊版的哈欠切出來，用人工切點檔的 `音效:名稱` 接進新版的句子，換掉原本的氣音。舊版的批次快取已經不在，這些檔案沒辦法重新產生，所以例外放進版控。

| 檔案（腳本名稱） | 舊版 m4a 的位置 | 音量調整 |
|---|---|---|
| `yawn_mianmian_1.wav`（哈欠棉棉1） | 98.70–101.20 秒（棉棉第一句的 `<yawn>`） | -4.5 dB |
| `yawn_lili.wav`（哈欠栗栗） | 115.50–117.60 秒（「你打哈欠了」和「咦」之間） | +0.6 dB |
| `yawn_gugu.wav`（哈欠咕咕爺爺） | 204.70–207.00 秒（「吸一口長長的氣」之後） | +0.6 dB |
| `yawn_mianmian_2.wav`（哈欠棉棉2） | 334.90–336.00 秒（「又想打了」之後） | -4.8 dB |
| `yawn_narrator.wav`（哈欠旁白） | 358.70–360.10 秒（「又打了一個小小的哈欠」之後） | -1.4 dB |

音量調整 = 新版同一角色說話的音量 − 舊版同一角色說話的音量（只算有聲音的 20ms 格），讓哈欠跟新版的台詞一樣大聲。處理：ffmpeg `atrim`、`volume`、淡入 0.03 秒、淡出 0.08 秒、升取樣到 24kHz。舊版有混背景，所以哈欠底下帶著約 -50 dB 的蟲鳴。

## 「晚安，為什麼森林」（自製，進版控）

ep11 旁白把結尾的「晚安，為什麼森林。」念成「晚安為森森林」，還拖到 4.5 秒。ep10 同一個聲音、同一句台詞、同一個 style 念對了，所以從 ep10 的人聲軌（`build/ep10_leaves.wav`，24kHz）照 `build/ep10_leaves.timeline.json` 最後一句的秒數（486.595–489.075）切出 `narrator_goodnight_forest.wav`（腳本名稱 `晚安森林`，2.48 秒），不調音量。在 ep11 旁白批次的人工切點檔寫一行只有 `音效:晚安森林`，整句換掉。語音辨識核對的就是這段錄音（「晚安為什麼森林」）。之後哪一集又念錯，也可以照樣換。

Wikimedia Commons 的檔案：在頁面上點「Download」或「Original file」即可下載，不用登入。

夜晚蟲鳴的備選（同樣是 CC0）：
- [AMBIENCE NIGHT FIELD CRICKET 01](https://freesound.org/people/sengjinn/sounds/175020/)（1:00）
- [Crickets calling at night, UK](https://freesound.org/people/chris_dagorne/sounds/181362/)（1:16）

河水的備選（CC0）：
- [Creek 06 (loop)](https://freesound.org/people/VKProduktion/sounds/231536/)（36 秒，作者做成可無縫循環，沒有突發聲，但水聲偏亮、偏嘶嘶聲）
- [River, stream, creek](https://freesound.org/people/kentspublicdomain/sounds/325182/)（30 秒，乾淨，但循環較短）

曾經用過、已換掉：
- 搖籃曲原本是 Commons 的[音樂盒版布拉姆斯〈搖籃曲〉](https://commons.wikimedia.org/wiki/File:Lullaby_wound_up_clock_guten_abend_gute_nacht.ogg)（Public domain，46 秒）。太短要循環，接縫有疑慮，改用蕭邦前奏曲。
- 搖籃曲的其他候選（試聽過、沒選）：Commons 的佛瑞〈搖籃曲〉、薩提〈吉諾佩第〉吉他版等，Musopen 蕭邦全集的夜曲 Op.9-2（太有名，難成為節目專屬聲音）等。

試過但不合用：
- [Gentle Stream](https://freesound.org/people/BurghRecords/sounds/446019/)（BurghRecords）：15.6、19.7、21、23.3 秒有鳥叫（約 1.8kHz／6kHz，比水聲大 8–11 dB），試聽時很突兀
- [Stream River Water Up Close](https://freesound.org/people/jackthemurray/sounds/433589/)：水聲起伏大，一分鐘約 20 次突出的潺潺聲
- Commons 的 [Hemlock stream](https://commons.wikimedia.org/wiki/File:Hemlock_stream.ogg)：8kHz、嚴重削峰

挑選新素材時，可以先下載 Freesound 頁面上的試聽 mp3（不用登入），分析有沒有「突然變大聲、又帶音高」的段落（鳥叫、蛙叫、人聲）。

## 沖繩與澎湖大冒險素材（tools/generate_adventure_assets.py）

全數透過數字訊號合成（DSP/Noise/FM）與 ffmpeg 演算法生成，100% 免版權、乾淨原創：
- okinawa_adventure_bgm.mp3：120 BPM 輕快跳躍夏日島嶼童趣音樂（木琴、烏克麗麗、低音貝斯）。
- penghu_adventure_bgm.mp3：116 BPM 甜美夢幻澎湖海島微風音樂（鐘琴、烏克麗麗、貝斯）。
- sfx_clap.wav / sfx_highfive.wav：拍手與清脆擊掌聲。
- sfx_applause.wav / sfx_cheer.wav：全場拍手鼓掌與歡呼聲。
- sfx_bubbles.wav / sfx_water_bubbles.wav / sfx_splash.wav：水族館氣泡、水中憋氣泡泡、水花飛濺。
- sfx_stomach.wav / sfx_sizzle.wav：肚子餓咕嚕叫、烤肉鐵板滋滋聲。
- sfx_airplane.wav：飛機呼嘯飛過（都卜勒調變音效）。
- sfx_waves.wav：沙灘海浪拍打潮汐聲。
- sfx_fireworks.wav / sfx_fireworks_muffled.wav：澎湖花火節煙火爆炸與戴耳塞後的沉悶煙火聲。
