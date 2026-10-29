# Why Forest｜Episode 2: Do fish sleep?

- 中文版：`episodes/ep02_fish.md`（[CHT] 為什麼森林｜第 2 集：魚會睡覺嗎？）
- 目標聽眾：3–6 歲、學英文的台灣孩子（也要讓英語母語的孩子聽得自然），睡前在床上聽
- 逐句翻譯：句數、順序、角色都跟中文版一樣（`tools/bilingual.py` 檢查）
- 本集知識點：魚也會睡覺，只是大部分的魚沒有眼皮，眼睛閉不起來；睡覺時會找安靜的地方，身體慢慢停下來休息

## 腳本格式說明（程式會讀）

- `@角色 {style} 台詞` → 一句語音；style 用簡短英文（官方建議），例如 {warm, slow}
- 台詞裡可以放英文的聲音標記：`<short pause>`、`<long pause>`、`<breath>`、`<exhales>`、`<chuckle>`、`<yawn>`、`<whispering>`
- `[停頓 N秒]` → 插入靜音
- `[音效 名稱]` → 插入音效（佔時間）；`[音效 名稱 疊]` → 疊在下一句底下（不佔時間）；`[音效 名稱 剪 自動]` → 自動剪掉前一句句尾被切斷的氣音再插入（也可寫秒數，例如 `剪 0.42秒`）
- `[背景 名稱]` → 從這裡開始循環播放背景（淡入，換下一段時交叉淡化）；`[背景 停]` → 淡出（`[背景 停 180秒]` 指定淡出長度）；`[背景 A B]` → 同時播多個
- `[共用 名稱]` → 插入 `episodes/shared.md` 裡的共用片段（每集一樣的開場、放鬆、咕咕爺爺登場）
- `[音量 -6dB]` → 之後的台詞都調小（或調大）這麼多，直到下一個 `[音量]`；只在組裝時處理，不影響配音快取
- 其他文字（標題、說明）程式會略過

---

## 一、開場儀式（約 40 秒，每集固定）

[共用 開場]

## 二、放鬆（約 40 秒，每集固定）

[共用 放鬆]

## 三、故事・前段（語速正常偏慢，可以有一點活潑）

[背景 河水]
@旁白 {storytelling, warm, slow} In the forest, there is a little river. The water is clear, and it flows slowly.
[停頓 1秒]
@旁白 {storytelling, warm} One evening, Lili the little squirrel sat by the river, with her best friend, Mumu the little bunny. Lili lives in a hole in the big oak tree. They looked at the little fish in the water.
[停頓 2秒]
@旁白 {storytelling, warm} The sky slowly got dark. The little fish swam slower, and slower.
[停頓 2秒]
@栗栗 {curious, whispering} Mumu, look at that one. It's hiding next to a rock. It's not moving at all.
[停頓 1秒]
@棉棉 {slow, soft} You're right…… Is it sleeping?
[停頓 1秒]
@栗栗 {curious, thinking hard} But its eyes are open. It's looking at us!
[停頓 1秒]
@棉棉 {slow, a little puzzled} When I sleep, I always close my eyes.
[停頓 1秒]
@栗栗 {curious, thoughtful} Why doesn't the fish close its eyes? Do fish sleep?
[停頓 1秒]
@棉棉 {slow, soft, yawning} <yawn> I don't know…… Let's go and ask Grandpa Gugu.
[停頓 2秒]

## 四、故事・中段：小實驗（語速慢，知識點講清楚）

[共用 咕咕爺爺登場]
@栗栗 {polite, quiet} Grandpa Gugu, Grandpa Gugu, do fish sleep?
[停頓 1秒]
@咕咕爺爺 {kind, chuckling} <chuckle> Yes, they do. Fish sleep, too. Let's do a little test, and you will see.
[停頓 1秒]
@咕咕爺爺 {gentle, guiding} Now, let's all pretend to be little fish. First, lie down. Let your body feel soft.
[停頓 2秒]
@旁白 {slow, soft} Lili and Mumu slowly lay down, on the grass by the river.
[停頓 2秒]
@咕咕爺爺 {gentle, guiding} Don't move your body. Keep your hands still. Keep your feet still. Like a little fish, breathe gently, and slowly.
[停頓 4秒]
@咕咕爺爺 {gentle, quiet} Now, are your eyes closed?
[停頓 1秒]
@栗栗 {quiet, thinking} Yes…… My eyes are closed.
[停頓 1秒]
@咕咕爺爺 {slow, clear, like sharing a secret} Fish don't have eyelids. Without eyelids, they can't close their eyes. So most fish keep their eyes open.
[停頓 2秒]
@咕咕爺爺 {slow, gentle} But they still sleep. When a fish sleeps, it finds a quiet place. It hides next to a rock, or in the water plants.
[停頓 2秒]
@咕咕爺爺 {slow, gentle} Then, its body slowly stops moving. Its breathing gets very, very slow. Its eyes are open, but it is really resting.
[停頓 2秒]
@棉棉 {slow, soft, amazed} So that little fish, was really sleeping.
[停頓 1秒]
@咕咕爺爺 {slow, a little awe} In the sea, there is a fish called the parrotfish. Before it sleeps, it blows lots and lots of bubbles, and wraps itself up. It's like a soft, clear sleeping bag.
[停頓 2秒]
@栗栗 {quiet, delighted} Wow, fish have blankets, too.
[停頓 1秒]
@咕咕爺爺 {very tender} That's right. Every animal has its own way to sleep. Some close their eyes. Some keep their eyes open. But at night, everyone has a good rest.
[停頓 3秒]

## 五、故事・後段：收進睡眠（越來越慢、越來越輕，不要再有驚喜或問題）

@旁白 {slowing down, softer} Lili gave a big, big yawn. <yawn> Mumu's ears slowly came down, too.
[停頓 2秒]
[音量 -3dB]
@棉棉 {very sleepy, soft} Good night, little fish……
[音量 0dB]
[停頓 2秒]
@栗栗 {very sleepy, soft} Good night, Mumu……
[停頓 2秒]
[背景 夜晚蟲鳴]
@旁白 {slower, softer} Mumu slowly walked home, to her little home in the grass. Lili climbed back into the hole in the oak tree. She curled up her tail, like a little blanket.
[停頓 3秒]
@旁白 {slower, softer} The river flowed gently, with no sound at all.
[停頓 3秒]
@旁白 {very slow, very soft} The little fish in the river quietly fell asleep, too.
[停頓 3秒]
@旁白 {very slow, almost whispering} The wind slowly became quiet. The leaves slowly became quiet, too.
[停頓 4秒]
@旁白 {very slow, almost whispering} Lili's eyes slowly, slowly close.
[停頓 4秒]
@咕咕爺爺 {whispering, very tender} Good night, Lili.
[停頓 5秒]

## 六、結尾儀式（每集固定）

[背景 搖籃曲]
@旁白 {very soft, very slow} Today, we found the answer to our why.
[停頓 3秒]
@旁白 {very soft, very slow} Now, it's your turn to close your eyes. You can sleep, just like the little fish.
[停頓 3秒]
[背景 停]
@旁白 {very soft, very slow, drawn out} Good night, Why Forest.
[停頓 3秒]

## 七、助眠尾段（約 10 分鐘，只有環境音，沒有說話）

[背景 夜晚蟲鳴慢 河水慢]
[停頓 420秒]
[背景 停 180秒]
[停頓 180秒]

---

## 製作備註（程式不會讀）

**節目說明（Show notes）草稿**（長度照 2026-10-29 重新生成的結果：故事 7 分 1 秒，全長 17 分 4 秒）
```
標題：[EN] Why Forest｜Episode 2: Do fish sleep?

A bedtime science story for kids ages 3–6, in simple English. The story is about 7 minutes, followed by 10 minutes of calming nature sounds to help your child drift off to sleep.

Lili the little squirrel and her friend Mumu are watching the fish in the river. One little fish is hiding next to a rock, not moving at all, but its eyes are wide open. Is it sleeping? Grandpa Gugu asks everyone to lie down and pretend to be little fish…

🐟 What we learn
Fish sleep, too! Most fish don't have eyelids, so they can't close their eyes. When they sleep, they find a quiet, safe place, stay very still, and breathe slowly. (The parrotfish's "bubbles" in our story are really a clear, slimy cover it makes around itself at night.)

👨‍👩‍👧 Parent tip
At bedtime, pretend to be little fish with your child. Keep your bodies very still, breathe slowly, and feel yourselves slowly relax.

⏱ The story is about 7 minutes, followed by 10 minutes of calming nature sounds (slowed-down crickets and a flowing stream), fading out over the last 3 minutes. About 17 minutes in total.

Story co-created by humans and AI. Voices generated by AI (Gemini TTS).

Chinese version: [CHT] 為什麼森林｜第 2 集：魚會睡覺嗎？

Next episode: Why do we yawn?

📷 Instagram: @whyforest.tw

Subtitle: A bedtime science story in simple English: do fish sleep, even with their eyes open?
Summary: Lili the little squirrel and her friend Mumu find a little fish by a rock, very still but with its eyes wide open. Grandpa Gugu asks everyone to lie down and pretend to be little fish, to find out if fish sleep. A 7-minute story for kids ages 3–6, followed by 10 minutes of calming nature sounds.
Tags: bedtime story, kids podcast, sleep story, English for kids, simple English, science for kids, fish, why questions, preschool, Why Forest, 睡前故事, 兒童英文, 英文睡前故事, 親子共讀, 為什麼森林
```

**關鍵單字（Key words）**
| word | 中文 | example |
|---|---|---|
| fish | 魚 | Do fish sleep? |
| river | 河 | In the forest, there is a little river. |
| rock | 石頭 | It's hiding next to a rock. |
| eyelids | 眼皮 | Fish don't have eyelids. |
| breathe | 呼吸 | Like a little fish, breathe gently, and slowly. |
| quiet | 安靜的 | When a fish sleeps, it finds a quiet place. |
| bubbles | 泡泡 | It blows lots and lots of bubbles. |
| rest | 休息 | Its eyes are open, but it is really resting. |

**在地化紀錄**
- 這集沒有雙關語或諧音梗，沒有需要改寫的知識內容；以下是為了短句和自然語感做的調整：
- 「這天傍晚，住在大橡樹樹洞裡的小松鼠栗栗，和好朋友小兔子棉棉，一起蹲在河邊，看水裡的小魚。」→ 拆成三個短句：One evening, Lili… sat by the river, with… Mumu… / Lili lives in a hole in the big oak tree. / They looked at the little fish in the water.（「蹲」crouch 太難，用 sat；One evening 跟第 1 集一致）
- 「牠躲在石頭旁邊，一動也不動」→ It's hiding next to a rock. It's not moving at all.
- 「真的耶……牠是不是在睡覺呀？」→ You're right…… Is it sleeping?（「真的耶」照第 1 集譯成 You're right）
- 「我們都來當一條小魚」→ let's all pretend to be little fish（直譯 be little fish 意思不清楚；pretend 是國小常見字）
- 「小實驗」→ a little test（同第 1 集）
- 「手不動，腳也不動」→ Keep your hands still. Keep your feet still.
- 「鸚哥魚」→ parrotfish（英文名剛好也是「鸚鵡魚」，孩子好記）
- 「吐出好多好多的泡泡」→ blows lots and lots of bubbles：照中文版保留「泡泡」的童趣說法（實際上是黏液，使用者決定保留）；節目說明的 What we learn 用括號補上比較精確的說法（a clear, slimy cover），跟中文版製作備註的建議一致。
- 「透明睡袋」→ a soft, clear sleeping bag（transparent 太難）
- 「魚也有被子」→ fish have blankets, too
- 「大家都會好好地休息」→ everyone has a good rest
- 「耳朵也慢慢垂下來了」→ Mumu's ears slowly came down, too.（droop 太難，同第 1 集）
- 「棉棉慢慢地走回草叢裡的家……當作小被子」→ 照第 1 集同一句的譯法，兩集一致。
- 「河水，輕輕地流著，沒有一點聲音」→ The river flowed gently, with no sound at all.
- 「小魚和你，一起睡覺」→ You can sleep, just like the little fish.（直譯 The little fish and you, sleep together 不自然）
- 後段時態：跟第 1 集一樣，故事用過去式，最後一句旁白「Lili's eyes slowly, slowly close.」用現在式，讓聽的孩子覺得「現在」也一起閉眼睛。
- 中文版的 `[音量]` 沒有抄（照中文配音量的），生成後重新量。

**知識點**：照中文版的查核（NOAA：大部分的魚沒有眼皮、魚會找安全角落靜止休息；Grutter et al. 2011：鸚哥魚夜間的黏液繭），沒有新增事實。

**生成紀錄（2026-10-29 整集重新生成）**
- 使用者要求照原腳本整集重新配音（台詞、style 都沒改）。舊的那次（2026-10-19 生成、10-20 修過切點）的四批配音、切點檔和 mp3 備份在 `build/_backup/ep02_fish_en_2026-10-20/`，移出 `build/segments/` 才能重新呼叫 API（快取鍵相同；舊的旁白切點檔也一起移走，不然會套到新音檔上）。
- 旁白、栗栗、棉棉、咕咕爺爺共 4 次 API；英文共用片段用快取。栗栗、咕咕爺爺靠靜音切開，旁白、棉棉靠語音辨識。
- 逐句辨識核對：栗栗第 5 句的「Yes……」和第 7 句的「Good」念得很輕（約 -40～-50 dB），自動切句當成靜音切掉了（第 5 句整個少了 Yes、第 7 句少了 Good）。寫人工切點 `build/segments/batch_095ae47b97a6264f.cuts.txt`：第 5 句改從 27.90 開始、第 7 句改從 41.70 開始，其他照自動切句的位置；兩段單獨辨識都對（yes my eyes are closed／good night momo）。其他句沒有重複、漏念或句首多出來的聲音。
- trim_tails：沒有要剪的句尾；旁白第 13 句（Why Forest 聽成 yforest）、栗栗第 7 句（Mumu 聽成 momo）的最後一個字辨識不出來，列入試聽。
- 音量（人聲軌每句有聲框平均）：舊配音加的 `[音量 -1dB]`／`[音量 -2dB]`（後段旁白、結尾第 1 句）拿掉，新配音這幾句本來就在 -19.5～-22.4。後段最大聲的是棉棉「Good night, little fish……」（-16.9），加 `[音量 -3dB]` 調到 -19.2。調整後後段和結尾約 -19.2～-24.8，中段約 -18～-24。前段棉棉 `<yawn>` 那句 -15.8 dB 仍是整集最大聲（在前段，沒調）；栗栗「Yes…… My eyes are closed.」-29.5、「Wow, fish have blankets, too.」-27.5 比較小聲（style 是 quiet），列入試聽。
- mp3：-17.2 LUFS、峰值 -0.8 dBFS；故事 7 分 1 秒，全長 17 分 4 秒。

**試聽時要特別注意的字**
- 名字：Lili、Mumu（MOO-moo，不要念成 MUH-muh）、Grandpa Gugu（不要念成 Google）
- parrotfish、eyelids 要念清楚
- `<yawn>` 有兩處（棉棉前段、旁白後段）：念得不好的話，可以照中文版換成同一個角色的哈欠錄音，要先問使用者
- 關鍵單字的句子：rock、eyelids、breathe、quiet、bubbles、resting
- 句首要特別聽（You're right……、Yes……、So that little fish……、Wow……）
