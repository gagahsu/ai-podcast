# Why Forest｜Episode 1: Why does the moon follow me?

- 中文版：`episodes/ep01_moon.md`（[CHT] 為什麼森林｜第 1 集：為什麼月亮會跟著我走？）
- 目標聽眾：3–6 歲、學英文的台灣孩子（也要讓英語母語的孩子聽得自然），睡前在床上聽
- 逐句翻譯：句數、順序、角色都跟中文版一樣（`tools/bilingual.py` 檢查）
- 本集知識點：越遠的東西，走路時看起來動得越慢；月亮非常非常遠，所以不管走到哪裡，它看起來都一直在頭上陪著我們

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

[背景 夜晚蟲鳴 河水]
@旁白 {storytelling, warm, slow} At the edge of the forest, there is a big, big oak tree. In a hole in the oak tree, lives a little squirrel. Her name is Lili.
[停頓 1秒]
@旁白 {storytelling, warm} Lili loves to ask questions. Why is the sky blue? Why does the rain fall down? Every day, Lili has so many whys.
[停頓 2秒]
@旁白 {storytelling, warm} One evening, Lili and her best friend, Mumu the little bunny, walked home from the river. The sky slowly got dark. A big, round moon came up from behind the mountain.
[停頓 2秒]
@栗栗 {delighted, quietly excited} Mumu, look! The moon is following us!
[停頓 1秒]
@棉棉 {slow, soft} You're right…… When we walk, it walks too.
[停頓 1秒]
@旁白 {a little playful} Lili walked faster. The moon went faster, too. Lili stopped. The moon stopped, too.
[停頓 1秒]
@栗栗 {curious, thinking hard} Does the moon, want to come home with us?
[停頓 1秒]
@棉棉 {slow, soft} I don't know…… Let's go to the big oak tree, and ask Grandpa Gugu.
[停頓 2秒]

## 四、故事・中段：小實驗（語速慢，知識點講清楚）

[背景 夜晚蟲鳴]
[共用 咕咕爺爺登場]
@栗栗 {polite, quiet} Grandpa Gugu, Grandpa Gugu, why does the moon keep following us?
[停頓 1秒]
@咕咕爺爺 {kind, chuckling} <chuckle> What a good question. Let's do a little test, and you will see.
[停頓 1秒]
@咕咕爺爺 {gentle, guiding} First, lie down. Let your body feel soft. Now, slowly close your eyes.
[停頓 3秒]
@咕咕爺爺 {gentle, guiding, slow} Imagine you are walking in the forest at night. There is a little white flower by the path. Far, far away, there is a mountain. And up in the sky, there is a big, round moon.
[停頓 3秒]
@咕咕爺爺 {gentle, guiding, slow} Now, imagine we are on the little path. Let's slowly take ten steps.
[停頓 1秒]
@旁白 {counting slowly, one by one} One, two, three, four, five, six, seven, eight, nine, ten.
[停頓 2秒]
@咕咕爺爺 {gentle, asking softly} Where is the little white flower now?
[停頓 1秒]
@棉棉 {slow, soft} Oh…… The little white flower is far behind us now.
[停頓 1秒]
@咕咕爺爺 {gentle, asking softly} And the mountain, far, far away?
[停頓 1秒]
@栗栗 {looking closely, thinking} The mountain…… moved just a tiny bit.
[停頓 1秒]
@咕咕爺爺 {gentle, asking softly} And the moon up in the sky?
[停頓 1秒]
@栗栗 {surprised but quiet} The moon didn't move at all! It's still right above us!
[停頓 2秒]
@咕咕爺爺 {slow, clear, like sharing a secret} That's the answer. When something is near us, and we walk, it goes behind us. When something is far away, it looks like it moves slowly.
[停頓 2秒]
@咕咕爺爺 {slow, a little awe} The moon is very, very far away. If you walk and walk, and never stop, it takes about nine years to get to the moon.
[停頓 2秒]
@咕咕爺爺 {slow, gentle} The moon is so, so far away. So wherever we go, it always looks like it's right above us. It looks like it's following us.
[停頓 2秒]
@栗栗 {thoughtful, trailing off} So…… the moon isn't chasing me?
[停頓 1秒]
@咕咕爺爺 {very tender} No, it isn't chasing you. But look. Tonight, every little animal in the forest can look up, and see the same moon.
[停頓 1秒]
@咕咕爺爺 {very tender, slowing down} The moon stays up in the sky, and gently keeps everyone company.
[停頓 3秒]

## 五、故事・後段：收進睡眠（越來越慢、越來越輕，不要再有驚喜或問題）

[音量 -2dB]
@旁白 {slowing down, softer} Lili and Mumu gave a big, big yawn. <yawn> Their ears and their eyelids slowly came down.
[音量 0dB]
[停頓 2秒]
@棉棉 {very sleepy, soft} Good night, Lili……
[停頓 2秒]
@栗栗 {very sleepy, soft} Good night, Mumu……
[停頓 2秒]
[音量 -2dB]
@旁白 {slower, softer} Mumu slowly walked home, to her little home in the grass. Lili climbed back into the hole in the oak tree. She curled up her tail, like a little blanket.
[音量 0dB]
[停頓 3秒]
@旁白 {slower, softer} Silver moonlight came softly into the tree hole. It fell warm and gentle on her blanket.
[停頓 3秒]
@旁白 {very slow, very soft} Lili looked at the moon outside, and quietly said in her heart: You're still here.
[停頓 3秒]
@旁白 {very slow, very soft} In the grass, the little bugs are still softly singing their little songs.
[停頓 3秒]
@旁白 {very slow, almost whispering} The wind slowly became quiet. The leaves slowly became quiet, too.
[停頓 4秒]
@旁白 {very slow, almost whispering} The moonlight shines softly. Lili's eyes slowly, slowly close.
[停頓 4秒]
@咕咕爺爺 {whispering, very tender} Good night, Lili.
[停頓 5秒]

## 六、結尾儀式（每集固定）

[背景 搖籃曲]
[音量 -1dB]
@旁白 {very soft, very slow} Today, we found the answer to our why.
[音量 0dB]
[停頓 3秒]
@旁白 {very soft, very slow} Now, it's your turn to close your eyes. The moon will stay with you, outside your window.
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

**節目說明（Show notes）草稿**（長度照 2026-10-19 生成結果：故事 8 分 5 秒，全長 18 分 8 秒）
```
標題：[EN] Why Forest｜Episode 1: Why does the moon follow me?

A bedtime science story for kids ages 3–6, in simple English. The story is about 8 minutes, followed by 10 minutes of calming nature sounds to help your child drift off to sleep.

Lili the little squirrel and her friend Mumu are walking home, when they notice something funny. The moon seems to follow them everywhere! Does the moon want to come home with them? Grandpa Gugu asks everyone to close their eyes, and take ten steps through the forest in their imagination…

🌕 What we learn
Things that are close to us seem to move fast and fall behind us when we walk. Things that are far away seem to move very slowly. The moon is very, very far away (if you could walk there without stopping, it would take about nine years!). So wherever we go, it looks like it stays right above us.

👨‍👩‍👧 Parent tip
At bedtime, lie down with your child, close your eyes, and imagine taking ten steps together. You can also talk about the gentle moon in the sky, and how its light keeps us company at night.

⏱ The story is about 8 minutes, followed by 10 minutes of calming nature sounds (slowed-down crickets and a flowing stream), fading out over the last 3 minutes. About 18 minutes in total.

Story co-created by humans and AI. Voices generated by AI (Gemini TTS).

Chinese version: [CHT] 為什麼森林｜第 1 集：為什麼月亮會跟著我走？

Next episode: Do fish sleep?

📷 Instagram: @whyforest.tw
```

**關鍵單字（Key words）**
| word | 中文 | example |
|---|---|---|
| moon | 月亮 | The moon is following us! |
| follow | 跟著 | Why does the moon keep following us? |
| walk | 走路 | When we walk, it walks too. |
| flower | 花 | There is a little white flower by the path. |
| mountain | 山 | Far, far away, there is a mountain. |
| far away | 很遠 | The moon is very, very far away. |
| sky | 天空 | And up in the sky, there is a big, round moon. |
| close your eyes | 閉上眼睛 | Now, slowly close your eyes. |

**在地化紀錄**
- 這集沒有雙關語或諧音梗，沒有需要改寫的知識內容；以下是為了短句和自然語感做的調整：
- 棉棉的英文名是 **Mumu**（念 MOO-moo）：原本音譯 Mianmian，第一次生成後使用者覺得英文念起來太奇怪，2026-10-18 改成 Mumu（疊字跟 Lili、Gugu 一致；母音 oo 跟 Lili 的 ee 不同，不會混；考慮過但沒選：Mify 念起來就是米飛兔 Miffy、Momo 會聯想到 momo 購物網和 Momo Challenge、Nini 跟 Lili 太像）。
- 「名字叫做栗栗」→ 加上 Her name is Lili，栗栗用 she（中文版沒有寫性別；使用者 2026-10-18 定 she，之後各集一致）。棉棉一樣用 her。
- 「栗栗每天都有好多好多的為什麼」→ Every day, Lili has so many whys.：保留「為什麼」當名詞的童趣說法，也呼應節目名 Why Forest。
- 「真的耶……」→ You're right……（直譯 Really 太短、語氣不對）。
- 「小實驗」→ a little test（experiment 對學英文的孩子太難）。
- 「離我們越近的東西，我們一走，它就跑到後面去。離我們越遠的東西，看起來就動得越慢。」→ 拆成 When something is near us… / When something is far away…（避免 the closer…, the faster… 比較級句型）。
- 「它在天上，溫柔地陪著每一個人」→ keeps everyone company（「陪」沒有更簡單的直譯）。
- 「耳朵和眼皮，慢慢地垂下來了」→ Their ears and their eyelids slowly came down.（droop 太難）。
- 「你還在呀」→ You're still here.
- 「月亮，會在窗外陪著你」→ The moon will stay with you, outside your window.
- 「晚安，為什麼森林」→ Good night, Why Forest.（固定說法）
- 後段時態：中文沒有時態；英文前面用過去式說故事，最後兩句旁白（The moonlight shines softly… / Lili's eyes slowly close）改用現在式，讓聽的孩子覺得「現在」也一起閉眼睛。蟲鳴那句也是現在式（the little bugs are still softly singing）。

**知識點**：照中文版的查核（視差、月球平均距離約 38.4 萬公里、不停地走約 8.77 年 → 「about nine years」），沒有新增事實。

**生成紀錄（2026-10-18）**
- 第一次生成：英文共用片段（旁白）、旁白、栗栗、棉棉、咕咕爺爺共 5 次＋英文 Reel 旁白 1 次。
- 名字改成 Mumu 之後，旁白、栗栗兩批重新生成（2 次；棉棉自己的台詞和咕咕爺爺、共用片段沒有提到她，不用重做）。舊的 Mianmian 版批次音檔留在 build/segments/。
- 栗栗（Mianmian 版）：靜音切得開，但核對時 Gugu 被聽成 goo goo（兩個字），一句有兩次 Grandpa Gugu，差 4 個字超過容許。內容是對的；程式加了英文名字的誤聽對照（`EN_NAME_ALIASES`，只用在比對）。
- 棉棉第 2 句：句尾 2.4 秒後有一口大聲的吸氣（trim_tails 因為名字分不清句尾，沒剪），寫人工切點 `build/segments/batch_ce444b46c5dcb660.cuts.txt` 剪到 Gugu 念完。
- 逐句辨識核對：沒有重複、多念、漏念。
- 旁白（Mumu 版）：語音辨識自動切開，但逐句核對交界時發現兩處切在單字中間（第 3→4 句切在 mountain、第 8→9 句切在 blanket 的字中短停頓；句尾少半個字、下一句開頭多半個字，內容差異在容許範圍內所以沒有警告），第 10 句 songs 的 s 太輕被切掉。寫人工切點 `build/segments/batch_b912eb2667cbf9af.cuts.txt` 改到句間的長靜音，每段單獨辨識都對。
- 音量（人聲軌每句有聲框平均，Mumu 版）：中段約 -20～-21 dB；後段旁白第 36、39 句和結尾第 1 句比中段大，加 `[音量 -2dB]`／`[音量 -1dB]` 調到約 -19.5～-20.5。

**試聽時要特別注意的字**
- 名字：Lili（不要念成 Lily 也沒關係，但要聽起來像名字）、Mumu（要念成 MOO-moo，不要念成 MUH-muh）、Grandpa Gugu（不要念成 Google）
- 數數 one 到 ten 要平穩、慢
- `<yawn>` 有沒有念成真的哈欠（不好的話，可以照中文版換成同一個角色的哈欠錄音，要先問使用者）
- 關鍵單字的句子：following、mountain、far away、close your eyes
- 句首要特別聽（Oh……、The mountain……、So……）
