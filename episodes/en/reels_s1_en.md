# Why Forest｜第一季英文 Reel 旁白（草稿，還沒生成）

`episodes/reels_s1.md` 的英文版，給 `../forestreels` 做英文精華 Reel 用，不是一集節目。結構一樣：旁白提問 → 角色選段（從英文正片剪）→ 旁白導流，觀眾是滑手機的**家長**，旁白跟貼文都全英文。

- 只有旁白一個角色，整份一批：生成一次只花 **1 次 API**。改任何一個字、style 或順序，整批都要重新生成，所以定稿後再生成。
- 這裡的 13 個問題就是英文版各集的標題問題（`[EN] Why Forest｜Episode N: <問題>`）。英文集數腳本第一行的問題要跟這裡一字不差。
- 語氣跟正片不同：對家長說話，溫暖但有精神，不要哄睡的語氣。沒有背景音。
- forestreels 用台詞片段從 `build/reels_s1_en.timeline.json` 找到每句（`data/clips/<集名>_en.json` 的 `hook`／`outro`）。

---

## 提問（每集一句）

@旁白 {warm, clear, inviting, talking to a parent, not sleepy} Your child asks, "Why does the moon follow me?" What would you say?
[停頓 1秒]
@旁白 {warm, clear, inviting, talking to a parent, not sleepy} Your child asks, "Do fish sleep?" What would you say?
[停頓 1秒]
@旁白 {warm, clear, inviting, talking to a parent, not sleepy} Your child asks, "Why do we yawn?" What would you say?
[停頓 1秒]
@旁白 {warm, clear, inviting, talking to a parent, not sleepy} Your child asks, "Why are there stars in the sky?" What would you say?
[停頓 1秒]
@旁白 {warm, clear, inviting, talking to a parent, not sleepy} Your child asks, "Why do fireflies glow?" What would you say?
[停頓 1秒]
@旁白 {warm, clear, inviting, talking to a parent, not sleepy} Your child asks, "Why do seeds grow?" What would you say?
[停頓 1秒]
@旁白 {warm, clear, inviting, talking to a parent, not sleepy} Your child asks, "Why does the sky get dark at night?" What would you say?
[停頓 1秒]
@旁白 {warm, clear, inviting, talking to a parent, not sleepy} Your child asks, "Why are owls awake at night?" What would you say?
[停頓 1秒]
@旁白 {warm, clear, inviting, talking to a parent, not sleepy} Your child asks, "Why do we need to sleep?" What would you say?
[停頓 1秒]
@旁白 {warm, clear, inviting, talking to a parent, not sleepy} Your child asks, "Why do leaves turn yellow in autumn?" What would you say?
[停頓 1秒]
@旁白 {warm, clear, inviting, talking to a parent, not sleepy} Your child asks, "Why does rain make sounds?" What would you say?
[停頓 1秒]
@旁白 {warm, clear, inviting, talking to a parent, not sleepy} Your child asks, "Why do cats purr?" What would you say?
[停頓 1秒]
@旁白 {warm, clear, inviting, talking to a parent, not sleepy} Your child asks, "Why do hugs make us feel safe?" What would you say?
[停頓 1秒]

## 導流（每集共用）

@旁白 {warm, gentle, inviting, talking to a parent} Find the full bedtime story on the Why Forest podcast. Listen together tonight.

---

## 製作備註（程式不會讀）

- 提問句固定同一個句型（Your child asks, "…" What would you say?），跟中文版一樣，系列感比較強。
- 「Why Forest」要聽是不是念得清楚、像節目名稱。
- 第 10 集用 autumn（台灣課本兩個都教；fall 在句子裡容易被聽成動詞「掉下來」）。
