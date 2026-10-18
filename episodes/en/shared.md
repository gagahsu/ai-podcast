# 共用片段（英文版）

`episodes/shared.md` 的英文版。英文集數腳本（`episodes/en/epNN_xxx_en.md`）用 `[共用 名稱]` 引用，名稱跟中文版一樣。

- 規則同中文版：這裡的台詞另成一批生成，快取在 `assets/shared_en/`（**進版控**），只有第一次花額度（只有旁白一個角色＝1 次 API）。
- **改這裡任何一個字、style 或句子順序，快取就失效**，要重新生成，而且新舊集數的聲音會不一樣。改之前先問使用者。
- 標記（`[背景]`、`[音效]`、`[停頓]`）跟中文版完全一樣，只翻譯台詞。呼吸聲素材（`吸氣1`、`吸氣2`、`吐氣`）是同一個旁白聲音（Sulafat）切出來的，英文版照用。
- 中文版的 `.cuts.txt`（剪掉 `<exhales>` 吐氣聲）不適用：英文版沒有那個標記。
- 用字原則：主要聽眾是學英文的台灣孩子，用簡單、常見的字，短句。

## 開場

[背景 搖籃曲]
[音效 開場鈴]
@旁白 {warm, soft} Hi, good night. Welcome to Why Forest.
[停頓 1秒]
@旁白 {gentle, slow} Now, pull up your blanket, and find your coziest spot.
[停頓 3秒]

## 放鬆

[背景 放鬆音樂]
@旁白 {very slow, very soft} Let's take a slow breath in, together.
[音效 吸氣1 剪 自動]
[停頓 1秒]
@旁白 {very slow, exhaling} And slowly, breathe out.
[音效 吐氣]
[停頓 1.5秒]
@旁白 {very slow, very soft} One more time. Breathe in.
[音效 吸氣2 剪 自動]
[停頓 1秒]
@旁白 {very slow, very soft} Breathe out.
[音效 吐氣]
[停頓 1.5秒]
@旁白 {gentle, smiling} Your little hands feel soft and floppy. Your little feet feel soft, too.
[停頓 2秒]
@旁白 {gentle, a little anticipation} Okay. Let's walk into the forest.
[停頓 3秒]

## 咕咕爺爺登場

[音效 貓頭鷹 疊]
@旁白 {warm, slow} Grandpa Gugu is an owl. He lives on the highest branch of the big oak tree. When everyone in the forest is asleep, Grandpa Gugu stays awake, and quietly watches over the forest.
[停頓 1秒]
