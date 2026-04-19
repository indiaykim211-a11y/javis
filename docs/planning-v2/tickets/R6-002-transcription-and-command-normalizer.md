# R6-002: Transcription and Command Normalizer

## 목적

음성을 텍스트로 바꾸고, 운영 intent 후보로 정규화한다.

## 범위

- transcript result model
- intent 후보 목록
- confidence / ambiguity 처리

## 완료 조건

- 핵심 운영 명령이 정규화된다
- 애매한 transcript는 clarification으로 빠진다
