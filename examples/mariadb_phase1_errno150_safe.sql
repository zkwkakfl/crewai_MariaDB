-- MariaDB: errno 150 (FK 타입 불일치) 방지 예시
-- 잘못된 예: FOREIGN KEY (work_order_no VARCHAR) REFERENCES work_orders(id INT)  → 절대 불가
-- 올바른 예는 아래 둘 중 하나로 통일

SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;

DROP DATABASE IF EXISTS smd_wo;
CREATE DATABASE smd_wo CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE smd_wo;

-- ── 패턴 A: 정수 surrogate key 로만 FK ─────────────────────────
CREATE TABLE work_orders (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    work_order_no VARCHAR(64) NOT NULL COMMENT '작업지시번호(업무 키)',
    customer_name VARCHAR(255) NOT NULL COMMENT '고객사',
    project_name VARCHAR(255) NOT NULL COMMENT '사업명',
    product_name VARCHAR(255) NOT NULL COMMENT '품명',
    part_no VARCHAR(128) NOT NULL COMMENT '품번',
    process_code VARCHAR(64) NULL COMMENT '공정',
    cust_delivery_date DATE NULL COMMENT '고객사납품',
    material_receipt_note TEXT NULL COMMENT '자재입고수량(텍스트)',
    order_spec TEXT NULL COMMENT '발주사양',
    folder_label VARCHAR(512) NULL COMMENT '폴더명',
    bom_file_label VARCHAR(512) NULL COMMENT 'BOM파일명(표시용)',
    release_list_label VARCHAR(512) NULL COMMENT '발행리스트(표시용)',
    bom_rev VARCHAR(64) NULL COMMENT 'BOM 리비전(Phase1 비움)',
    pcb_rev VARCHAR(64) NULL COMMENT 'PCB 리비전(Phase1 비움)',
    metal_top_rev VARCHAR(64) NULL COMMENT '메탈 TOP(Phase1 비움)',
    metal_bot_rev VARCHAR(64) NULL COMMENT '메탈 BOT(Phase1 비움)',
    exported_at DATETIME(3) NOT NULL,
    biz_date DATE NULL,
    PRIMARY KEY (id),
    UNIQUE KEY uk_work_order_no (work_order_no)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='실파일(BOM/거버/좌표)은 DB 밖. 경로 조립: {네트워크루트}\\{고객사}\\{사업명}\\{품명(품번)}\\(BOM|원본좌표|거버파일)\\';

CREATE TABLE bom_info (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    work_order_id BIGINT UNSIGNED NOT NULL COMMENT 'work_orders.id 와 동일 타입',
    item_name VARCHAR(255) NOT NULL,
    part_no VARCHAR(128) NOT NULL,
    qty INT NULL,
    note TEXT NULL,
    PRIMARY KEY (id),
    KEY idx_bom_wo (work_order_id),
    CONSTRAINT fk_bom_work_order
        FOREIGN KEY (work_order_id) REFERENCES work_orders (id)
        ON UPDATE CASCADE ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

SET FOREIGN_KEY_CHECKS = 1;

-- 스테이징 적재 후 예시(컬럼 매핑은 실제 staging 정의에 맞게 조정):
-- INSERT INTO work_orders (work_order_no, customer_name, project_name, product_name, part_no, ...)
-- SELECT `작업지시번호`, `고객사`, `사업명`, `품명`, `품번`, ... FROM staging_consolidated;
