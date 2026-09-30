# CLAUDE.md

給 Claude Code 在這個 repo 工作時的說明。使用者介紹與完整用法見 README.md。

## 專案是什麼

兒童睡前故事 podcast「為什麼森林」的製作工具。`generate_episode.py` 讀一集的 Markdown 腳本，用 Gemini 3.8 TTS 配音，切句、插入停頓、組成一集，再用 ffmpeg 輸出 mp3。

- 使用者在台灣，用 Windows ＋ PowerShell 執行（指令請給 PowerShell 語法：`$env:X="..."`，不是 `export` 或 `set`），用 `py` 啟動 Python。
- 使用者有 NVIDIA RTX 3050（4GB），但 CUDA 函式庫不一定裝好，Whisper 預設用 CPU。
- 回覆與程式註解、訊息都用**繁體中文（台灣用語）**。

## 常用指令

**執行任何 Python 前一律先設 UTF-8，否則程式的中文輸出會變亂碼**（Windows 預設 cp950）：PowerShell 用 `$env:PYTHONUTF8="1"`；Bash 工具用 `export PYTHONUTF8=1`（或指令前加 `PYTHONUTF8=1`）。

```bash
python -m unittest discover -s tests -v                            # 離線測試（必跑）
python generate_episode.py episodes/ep01_moon.md --dry-run         # 解析腳本
PYTHONPATH=tests/fake python generate_episode.py episodes/ep01_moon.md --rpm 6000   # 用假 SDK 跑完整流程
```

`tests/fake/google/genai` 是假的 SDK，用 `FAKE_MODE=good|wav|long` 模擬不同回應。

## 絕對不要做的事

- **不要用真的 API 做測試或實驗。** 免費方案每個模型每天只有 10 次請求，一次試跑就可能用光一整天的額度。需要驗證就用假 SDK 或合成音訊；真的要打 API 時，先跟使用者確認，並用 `--limit`。
- **不要把導演提示、角色設定、停頓指示寫進台詞文字。** Gemini 3.8 TTS 會把 `text` 欄位全部念出來。語氣放 `speech_metadata.style`（簡短英文），停頓用 `[停頓 N秒]`（程式插入）或官方標記 `<long pause>`。
- **不要讓切句「猜」。** 切錯（句子錯位）比切不開糟糕得多。任何切句方法都要有「分不清就回傳失敗」的判斷，並用合成音訊測過「會不會在沒警告的情況下切錯」。曾經試過用字數比例＋動態規劃挑切點，模擬測試中大量無聲切錯，已放棄。
- **不要在切句失敗時自動重新生成。** 預設是停下來說明原因；改成逐句生成要使用者自己加 `--fallback`。
- **不要照抄 AI Studio playground 的「Get code」。** 它會漏掉 Style 設定。請以官方文件的 Interactions API 格式為準。

## 程式架構（generate_episode.py）

- `parse_script`：解析 `@角色 {style} 台詞` 和 `[停頓 N秒]`。
- `CHARACTERS`：角色 → (聲音, 基本風格英文)。`style_for` 把基本風格和每句的導演提示合併。
- `_call_api`：Interactions API（`client.interactions.create`），每段台詞帶 `annotations=[{"type": "speech_metadata", "style": ...}]`。依 `--rpm` 排隊；429 依伺服器建議秒數重試；每日額度用完就結束。錯誤類別不固定，用 `status_code` / `code` 判斷。
- `Audio`：16-bit 單聲道 PCM ＋ 取樣率。API 可能回 raw PCM 或 WAV，`from_api` 兩種都處理；快取存成 WAV。
- 快取鍵：`sha1(模型|聲音|送出內容)`。**改動送出內容的格式（分隔標記、style 組法）會讓所有快取失效**，使用者就得重新花額度，改之前要想清楚並告知使用者。
- 切句：
  1. `split_on_silence`：嚴格靜音切割。`_silent_runs` 會把中間只夾著短雜音（< `BLIP_SEC`）的兩段靜音合併。
  2. `split_with_whisper`：faster-whisper 逐字時間戳 → `align_cuts` 與腳本逐字對齊（`_to_simplified` 先統一繁簡）→ 在交界字之間的靜音下刀 → 逐段檢查辨識內容與台詞的差異字數。
     **不要給 Whisper `initial_prompt`（台詞當提示）**：它會把提示續寫出來而不是聽音檔，開頭變亂碼。咕咕爺爺 12 句實測：有提示 1/4 對齊成功，沒提示 3/3，而且快 4 倍。換 medium 模型、開 VAD、關 `condition_on_previous_text` 都沒用。
  3. 都失敗 → 停下。
- `inspect_batches`：`--inspect`，列出批次音檔的靜音長度，除錯用，不呼叫 API。

## 腳本撰寫慣例（episodes/）

- 結構固定：開場儀式（含 AI 揭露）→ 放鬆引導 → 故事前段 → 中段（知識點／小實驗）→ 後段越來越慢、越來越輕 → 結尾儀式。
- 後段與結尾**不要再出現問題或驚喜**，避免把孩子叫醒。下集預告寫在節目說明，不放在音檔裡。
- 公版或原創故事才能用，不要改編受版權保護的繪本。
- 知識點要查核，查核過程寫在腳本最後的「製作備註」（程式不會讀）。
- 注意多音字和專有名詞（例如「栗栗」唸 lì lì），念錯時優先改寫句子避開。

## 待辦／未驗證

- Whisper 對齊切句已用 ep01 的真音檔驗證（旁白 23 句、咕咕爺爺 12 句都切開），但只有這一集。切句後的內容檢查容許差 2 個字，所以「句首或句尾只少一個字」抓不到（曾發生：句首的「咕」被當雜訊吃掉，是靠人耳聽出來的）。新的一集生成後，要特別聽每個角色的句首。
- 還沒選定台灣口音的聲音；目前旁白是 Sulafat（使用者在 playground 也試過 Tova）。
- 還沒決定要用 3.8 Flash 還是 Lite。
