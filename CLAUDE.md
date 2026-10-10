# CLAUDE.md

給 Claude Code 在這個 repo 工作時的說明。使用者介紹與完整用法見 README.md。

## 專案是什麼

兒童睡前故事 podcast「為什麼森林」的製作工具。`generate_episode.py` 讀一集的 Markdown 腳本，用 Gemini 3.8 TTS 配音，切句、插入停頓、組成一集，再用 ffmpeg 輸出 mp3。

- 使用者在台灣，用 Windows ＋ PowerShell 執行（指令請給 PowerShell 語法：`$env:X="..."`，不是 `export` 或 `set`），用 `py` 啟動 Python。
- 使用者有 NVIDIA RTX 3050（4GB），但 CUDA 函式庫不一定裝好，Whisper 預設用 CPU。
- 回覆與程式註解、訊息都用**繁體中文（台灣用語）**。

## 新的一集

用專案 skill `/new-episode`（`.claude/skills/new-episode/SKILL.md`）：使用者只給題目，或什麼都不給讓 Claude 照 `episodes/TOPICS.md` 的季度規劃做下一集。skill 裡寫了完整流程（選題 → 腳本 → 查核 → 音效 → dry-run → 停下來等確認 → 生成 → 試聽清單）。改了腳本慣例或固定段落時，要同步更新 skill。

## 常用指令

**執行任何 Python 前一律先設 UTF-8，否則程式的中文輸出會變亂碼**（Windows 預設 cp950）：PowerShell 用 `$env:PYTHONUTF8="1"`；Bash 工具用 `export PYTHONUTF8=1`（或指令前加 `PYTHONUTF8=1`）。

```bash
python -m unittest discover -s tests -v                            # 離線測試（必跑）
python generate_episode.py episodes/ep01_moon.md --dry-run         # 解析腳本
PYTHONPATH=tests/fake python generate_episode.py episodes/ep01_moon.md --rpm 6000   # 用假 SDK 跑完整流程
```

每次組裝都會輸出 `build/<集名>.timeline.json`（每句的角色、台詞、在整集音檔裡的起訖秒數，給 `../forestreels` 做 Reel 用；`write_timeline`）。已生成的集數用 `--offline --timeline-only` 從快取補出時間軸，不花額度、不重新輸出 wav/mp3。

`episodes/reels_s1.md` 不是一集節目，是給 forestreels 精華 Reel 用的旁白（13 集的開場提問＋共用片尾導流，對家長說話），只有旁白一批、整份 1 次 API，已生成。改任何字都要整批重新生成。

`tests/fake/google/genai` 是假的 SDK，用 `FAKE_MODE=good|wav|long` 模擬不同回應。

## 絕對不要做的事

- **不要用真的 API 做測試或實驗。** 免費方案每個模型每天只有 10 次請求，一次試跑就可能用光一整天的額度。需要驗證就用假 SDK 或合成音訊；真的要打 API 做實驗時，先跟使用者確認，並用 `--limit`。（正式生成一集時不要先 `--limit` 試聽：分批模式下部分句子的批次內容跟整集不同，快取用不到，等於多花額度。）
- **不要把導演提示、角色設定、停頓指示寫進台詞文字。** Gemini 3.8 TTS 會把 `text` 欄位全部念出來。語氣放 `speech_metadata.style`（簡短英文），停頓用 `[停頓 N秒]`（程式插入）或官方標記 `<long pause>`。
- **不要讓切句「猜」。** 切錯（句子錯位）比切不開糟糕得多。任何切句方法都要有「分不清就回傳失敗」的判斷，並用合成音訊測過「會不會在沒警告的情況下切錯」。曾經試過用字數比例＋動態規劃挑切點，模擬測試中大量無聲切錯，已放棄。
- **不要在切句失敗時自動重新生成。** 預設是停下來說明原因；改成逐句生成要使用者自己加 `--fallback`。
- **不要照抄 AI Studio playground 的「Get code」。** 它會漏掉 Style 設定。請以官方文件的 Interactions API 格式為準。

## 程式架構（generate_episode.py）

- `parse_script`：解析 `@角色 {style} 台詞` 和 `[停頓 N秒]`。
- 共用片段：每集一樣的開場、放鬆、咕咕爺爺登場寫在 `episodes/shared.md`（`## 名稱` 分段），集數腳本用 `[共用 名稱]` 引用，`expand_shared` 展開。共用的台詞另成一批（每個角色一批），快取在 `assets/shared/`（**進版控**），所以每集的招牌段落聲音都一樣，生成一次之後不再花額度。改 shared.md 的任何字、style 或順序都會讓這批快取失效、要重新生成，新舊集的聲音也會不同，改之前要先問使用者。ep01–ep03 原本把這些段落直接寫在腳本裡（舊做法），現已全部升級為引用 shared.md。
- `CHARACTERS`：角色 → (聲音, 基本風格英文)。`style_for` 把基本風格和每句的導演提示合併。
- `_call_api`：Interactions API（`client.interactions.create`），每段台詞帶 `annotations=[{"type": "speech_metadata", "style": ...}]`。依 `--rpm` 排隊；429 依伺服器建議秒數重試；每日額度用完時，`Gemini` 包裝類別會從免費 key 換成 `GEMINI_API_KEY_PAID`（沒設或加 `--no-paid` 就結束）。金鑰從 `.env` 讀（`load_env`，**.env 有填的值優先**，蓋掉環境變數：Windows 使用者環境變數裡的舊 key 曾默默蓋掉 .env 的新 key。測試設 `NO_DOTENV=1` 不讀 .env）。**不要做多帳號輪替 key**：用多個帳號繞過免費額度違反 Gemini API 條款，使用者已確認不做。錯誤類別不固定，用 `status_code` / `code` 判斷。請求超過 `API_TIMEOUT_SEC` 就停下、**不自動重試**（伺服器可能已生成完、已算額度；ep06 曾因伺服器斷線而無逾時，卡了 10 分鐘以上）。
- `Audio`：16-bit 單聲道 PCM ＋ 取樣率。API 可能回 raw PCM 或 WAV，`from_api` 兩種都處理；快取存成 WAV。
- 快取鍵：`sha1(模型|聲音|送出內容)`。**改動送出內容的格式（分隔標記、style 組法）會讓所有快取失效**，使用者就得重新花額度，改之前要想清楚並告知使用者。
- 切句：
  1. `split_on_silence`：嚴格靜音切割。`_silent_runs` 會把中間只夾著短雜音（< `BLIP_SEC`）的兩段靜音合併。切開後一定要經過 `check_pieces`（逐句語音辨識、跟台詞比對）：ep04 旁白多念一句、又有兩句之間只停 1.1 秒被黏在一起，句數剛好對上，靜音切割「成功」但整段錯位，以前完全沒有警告。離線測試用合成音訊，所以 `run()` 設 `ASR_CHECK=0`。
  2. `split_with_whisper`：faster-whisper 逐字時間戳 → `align_cuts` 與腳本逐字對齊（`_to_simplified` 先統一繁簡）→ 在交界字之間的靜音下刀 → 逐段檢查辨識內容與台詞的差異字數。
     **不要給 Whisper `initial_prompt`（台詞當提示）**：它會把提示續寫出來而不是聽音檔，開頭變亂碼。咕咕爺爺 12 句實測：有提示 1/4 對齊成功，沒提示 3/3，而且快 4 倍。換 medium 模型、開 VAD、關 `condition_on_previous_text` 都沒用。
  3. 都失敗 → 停下。
  - 人工切點：批次音檔旁放 `<批次檔名>.cuts.txt`（每行一句「開始秒 結束秒」；一行寫好幾組就接起來，可以剪掉句中不要的聲音），`manual_cuts` 就照它切，切完一樣經過 `check_pieces` 核對，不自動切、不花額度。用在音檔本身能用、但模型念錯的時候（ep04 棉棉把一句念了兩次，對齊必然失敗）。秒數由 Claude 用 `transcribe_chars`／`_silent_runs` 離線找出、對每段單獨辨識確認，再請使用者試聽。集數的切點檔在 `build/`（不進版控），共用片段的在 `assets/shared/`（進版控；ep04 時用它剪掉了 `<exhales>` 念出來的短吐氣聲，見 shared.md 說明），換了台詞或 style 快取鍵就變，舊的切點檔自然不會被用到。秒數後面寫 `人耳確認` 的那一行不做語音辨識核對，用在很輕的氣音（ep01 咕咕爺爺的「晚安，栗栗」被聽成「哇蜜蜜」「哇莉莉」，每次都不一樣）；**只有使用者親耳聽過、確認內容對了才能加**，Claude 不能自己判斷後加上。兩組秒數之間可以寫 `音效:名稱`（`SOUNDS` 裡的名稱），把那個音效接進句子裡、換掉模型念得不好的聲音標記；語音辨識核對只聽台詞部分（`speech_only`）。ep03 的 `<yawn>` 只念成一口氣，就是這樣換成舊版配音切出來的哈欠（`assets/yawn_*.wav`，見 SOURCES.md）。一行也可以只寫 `音效:名稱`、不寫秒數：整句換成那段錄音，語音辨識核對那段錄音本身（ep11 旁白把「晚安，為什麼森林」念成「為森森林」，換成 ep10 念對的那次，`assets/narrator_goodnight_forest.wav`）。**整批一起辨識時，Whisper 可能把模型重複念的句子吃掉**：ep11 咕咕爺爺把一句念了兩次，對齊「成功」、句子都對得上，重複的那次卻留在下一句開頭，是 `--offline` 重跑時逐句核對才發現的。生成後要對每個自動切出來的句子單獨辨識一次，句子明顯比台詞長的要特別看。
- `inspect_batches`：`--inspect`，列出批次音檔的靜音長度，除錯用，不呼叫 API。
- `tools/trim_tails.py`：生成後檢查句尾。Gemini 在下一句之前會大聲吸一口氣，自動切句常把它分到上一句句尾（ep07 使用者聽到像哈欠或喘氣，ep08 一集 7 句）。工具找出「最後一個字 → 安靜 → 一小段大聲的聲音」的句子，`--write` 寫成人工切點檔，句尾剪到念完；判斷靠語音辨識的最後一個字跟台詞同音（不比聲調），分不清就不剪。已有切點檔的批次只檢查不改寫，標「人耳確認」的句子跳過。`auto_split`／`batch_request` 是為了它從 `synthesize_batch` 抽出來的，自動切出來的每段有 `start`（在批次音檔裡的起點）。
- 音效與背景：`SOUNDS`：名稱 → (assets/ 裡的檔名, 相對人聲 dB)。`measure_lufs` 先量素材響度，所以 dB 跟素材原本多大聲無關。
  - `assemble`：插入型 `[音效 X]` 直接接進人聲軌；同時記下疊加音效、背景區段、說話區間的秒數。`[音量 -NdB]` 讓之後的台詞都調整 N dB（直到下一個 `[音量]`），只在組裝時處理，不影響快取鍵。用在 Gemini 把該輕的段落念得比較大聲時（ep06 後段比中段大 6–8 dB，style 寫 softer 也沒用）。
  - `mix`：ffmpeg `adelay` 定位、`amix normalize=0`。背景的 ducking 用 `volume` 運算式（`duck_expr`），**前面一定要有 `asetnsamples`**，否則 frame 太大，運算式約 0.5 秒才更新一次。
  - `export_mp3`：量整集響度 → 同一個固定增益 → 升取樣到 96kHz 再用 `alimiter` 壓峰值。**不要用 `loudnorm`**：Gemini 配音峰值本來就約 +0.6 dBTP，loudnorm 的 linear 模式做不到，會退回動態模式，在停頓時把背景拉大聲（ep02 實測）。不升取樣的話，mp3 真峰值會超過 0 dB。
  - ffmpeg 一律經過 `find_ffmpeg`，不要寫死 `"ffmpeg"`：這台電腦的 PATH 上有 miniconda 附的 4.3（Bash 工具會先找到它），不支援 `ebur128=framelog=quiet`、`amix normalize`。`find_ffmpeg` 依 PATH 順序用 `FFMPEG_PROBE` 試跑，挑第一個能用的；`.env` 設 `FFMPEG` 就只用那一個。用到新的濾鏡或選項時，要加進 `FFMPEG_PROBE`。
  - `--bgm` 會蓋掉腳本裡的 `[背景]`（使用者選的），不是兩者疊加。
  - 素材有缺少時，要在呼叫 API **之前**停下（`check_sounds`）。測試用 `ASSETS_DIR` 指向合成素材，不依賴使用者下載的檔案。
  - 音效只在組裝階段處理，不影響 TTS 快取鍵。
  - 背景在 `mix` 裡先 `acompressor`（門檻 = 這段背景的目標音量 + `BG_COMP_ABOVE`），鋼琴曲樂句變大聲時才不會蓋過說話。
- 呼吸聲：Gemini TTS **沒有吸氣標記**（只有 `<breath>`、`<heavy breath>`、`<exhales>`），而且標記都是一瞬間，不能拉長。所以放鬆段落的吸氣／吐氣是從 ep02 旁白配音切出來、用 rubberband 拉長 3–4 倍的素材（`assets/narrator_*.wav`，進版控，做法見 `assets/SOURCES.md`）。切句會把句尾的氣音當靜音切掉（吸氣只剩 0.4 秒），所以用 `[音效 吸氣1 剪 自動]` 剪掉殘段再接上：`trailing_breath` 只認「台詞 → 至少 0.15 秒停頓 → 比台詞小 15 dB 以上、不超過 1 秒的聲音」，分不清就不剪（多聽到半口氣沒關係，剪到台詞才糟）。ep02 實測自動量到 0.38／0.42 秒，跟人工量的一致。

## 腳本撰寫慣例（episodes/）

- 結構固定：開場儀式（含 AI 揭露）→ 放鬆引導 → 故事前段 → 中段（知識點／小實驗）→ 後段越來越慢、越來越輕 → 結尾儀式。
- 後段與結尾**不要再出現問題或驚喜**，避免把孩子叫醒。下集預告寫在節目說明，不放在音檔裡。
- 公版或原創故事才能用，不要改編受版權保護的繪本。
- 知識點要查核，查核過程寫在腳本最後的「製作備註」（程式不會讀）。
- 音效與背景在寫腳本時一併決定（`[音效 X]`、`[音效 X 疊]`、`[背景 X]`、`[背景 停]`），優先從 `SOUNDS` 現有素材挑；需要新素材時，加進 `SOUNDS` 並在 `assets/SOURCES.md` 記錄來源。寫完跑 `--dry-run` 確認素材都在。
- 慣例：搖籃曲（蕭邦前奏曲 Op.28-13）是節目招牌，每集固定：開場放 `[背景 搖籃曲]`＋`[音效 開場鈴]`，放鬆段開頭換 `[背景 放鬆音樂]`（Andrewkn〈Wandering〉），呼吸用 `[音效 吸氣1 剪 …]`／`[音效 吐氣]`，結尾儀式換回搖籃曲，最後一句前放 `[背景 停]`。故事段的環境音**跟著場景換**（ep02：河邊用 `河水`，栗栗回樹洞時換 `夜晚蟲鳴`）；環境音不要跟台詞矛盾（例如台詞說「沒有一點聲音」時還有水聲）。
- 「晚安，為什麼森林」之後接「助眠尾段」：約 10 分鐘只有環境音（ep04 起用 `[背景 夜晚蟲鳴慢 河水慢]`：atempo 放慢 0.7 倍的版本，使用者試聽後選的；ep02、ep03 是原速的 `夜晚蟲鳴 河水`。不用旋律，46 秒的音樂盒循環太單調），最後用 `[背景 停 180秒]` 慢慢淡出。用意是陪還沒睡著的孩子，並擋住 app 自動播下一集。節目說明要寫出故事與尾段各多長。
- 後段與結尾只能用持續、柔和的環境音，不要放有尖銳起音的音效（鈴、敲擊、動物叫聲），避免把孩子吵醒。
- 素材只用 CC0 或公有領域，素材檔不進版控（`.gitignore`），只記錄下載來源。
- 注意多音字和專有名詞（例如「栗栗」唸 lì lì），念錯時優先改寫句子避開。也可以在那句的 style 加 `pronounce 哈欠 as hā qiàn` 這類拼音提示（ep03 栗栗把「打哈欠」念成 hē，加了之後全部改對；只試過這一次）。改 style 會讓那個角色整批的快取失效。

## 待辦／未驗證

- Whisper 對齊切句已用 ep01 的真音檔驗證（旁白 23 句、咕咕爺爺 12 句都切開），但只有這一集。切句後的內容檢查容許差 2 個字，所以「句首或句尾只少一個字」抓不到（曾發生：句首的「咕」被當雜訊吃掉，是靠人耳聽出來的）。新的一集生成後，要特別聽每個角色的句首。
- 還沒選定台灣口音的聲音；目前旁白是 Sulafat（使用者在 playground 也試過 Tova）。
- 還沒決定要用 3.8 Flash 還是 Lite。
- 素材的 dB 設定是預估值，使用者只聽過 ep02 的部分版本。換成蕭邦前奏曲＋〈Wandering〉的完整 ep02 還要再聽一次。
- ep01 已重製為新流程腳本（共用片段、音效與背景、床上想像小實驗、助眠尾段）。
