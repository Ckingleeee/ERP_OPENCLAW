SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;

CREATE TABLE IF NOT EXISTS `benefit_provider` (
  `id` bigint NOT NULL AUTO_INCREMENT COMMENT '权益服务商ID',
  `provider_code` varchar(50) NOT NULL COMMENT '服务商编码',
  `name` varchar(100) NOT NULL COMMENT '服务商名称',
  `contact_person` varchar(50) DEFAULT NULL COMMENT '联系人',
  `phone` varchar(20) DEFAULT NULL COMMENT '联系电话',
  `email` varchar(100) DEFAULT NULL COMMENT '邮箱',
  `address` varchar(200) DEFAULT NULL COMMENT '地址',
  `service_rating` char(1) DEFAULT 'B' COMMENT '综合服务评级',
  `status` tinyint DEFAULT 1 COMMENT '合作状态',
  `deleted` tinyint DEFAULT 0 COMMENT '删除标志',
  `create_time` datetime DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `update_time` datetime DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_provider_code` (`provider_code`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='权益服务商表';

CREATE TABLE IF NOT EXISTS `marketing_resource` (
  `id` bigint NOT NULL AUTO_INCREMENT COMMENT '营销资源ID',
  `resource_code` varchar(50) NOT NULL COMMENT '资源编码',
  `name` varchar(100) NOT NULL COMMENT '权益或营销资源名称',
  `model` varchar(100) DEFAULT NULL COMMENT '型号',
  `specification` varchar(200) DEFAULT NULL COMMENT '规格',
  `unit` varchar(20) DEFAULT '份' COMMENT '计量单位',
  `unit_cost` decimal(10,2) NOT NULL DEFAULT 0.00 COMMENT '单位成本',
  `face_value` decimal(10,2) DEFAULT 0.00 COMMENT '权益面值',
  `quota_warning_value` int DEFAULT 100 COMMENT '配额预警值',
  `provider_id` bigint DEFAULT NULL COMMENT '权益服务商ID',
  `category` varchar(50) DEFAULT NULL COMMENT '分类',
  `description` text COMMENT '权益规则与适用场景',
  `deleted` tinyint DEFAULT 0 COMMENT '删除标志',
  `create_time` datetime DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `update_time` datetime DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_resource_code` (`resource_code`),
  KEY `idx_provider_id` (`provider_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='权益与营销资源表';

CREATE TABLE IF NOT EXISTS `resource_quota` (
  `id` bigint NOT NULL AUTO_INCREMENT COMMENT '配额ID',
  `resource_id` bigint NOT NULL COMMENT '营销资源ID',
  `current_quota` int NOT NULL DEFAULT 0 COMMENT '当前可用配额',
  `safety_quota` int DEFAULT 100 COMMENT '安全配额阈值',
  `last_replenished_time` datetime DEFAULT NULL COMMENT '最近补充时间',
  `last_redeemed_time` datetime DEFAULT NULL COMMENT '最近核销时间',
  `quota_pool` varchar(100) DEFAULT '通用权益池' COMMENT '资源池',
  `deleted` tinyint DEFAULT 0 COMMENT '删除标志',
  `create_time` datetime DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `update_time` datetime DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_resource_id` (`resource_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='权益资源配额表';

CREATE TABLE IF NOT EXISTS `resource_replenishment` (
  `id` bigint NOT NULL AUTO_INCREMENT COMMENT '资源补充单ID',
  `replenishment_number` varchar(50) NOT NULL COMMENT '补充单编号',
  `total_amount` decimal(12,2) DEFAULT 0.00 COMMENT '补充单总金额',
  `status` tinyint DEFAULT 1 COMMENT '1待审核 2已审核 3配置中 4已生效 5已取消',
  `replenishment_time` datetime DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `expected_activation_date` date DEFAULT NULL COMMENT '预计生效日期',
  `actual_activation_date` date DEFAULT NULL COMMENT '实际生效日期',
  `created_by` bigint DEFAULT NULL COMMENT '创建人ID',
  `remark` varchar(500) DEFAULT NULL COMMENT '备注',
  `deleted` tinyint DEFAULT 0 COMMENT '删除标志',
  `create_time` datetime DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `update_time` datetime DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_replenishment_number` (`replenishment_number`),
  KEY `idx_replenishment_time` (`replenishment_time`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='权益资源补充单';

CREATE TABLE IF NOT EXISTS `replenishment_detail` (
  `id` bigint NOT NULL AUTO_INCREMENT COMMENT '明细ID',
  `replenishment_id` bigint NOT NULL COMMENT '资源补充单ID',
  `resource_id` bigint NOT NULL COMMENT '营销资源ID',
  `quantity` int NOT NULL DEFAULT 1 COMMENT '补充数量',
  `unit_cost` decimal(10,2) NOT NULL DEFAULT 0.00 COMMENT '单位成本',
  `subtotal` decimal(12,2) GENERATED ALWAYS AS (`quantity` * `unit_cost`) STORED COMMENT '小计金额',
  `remark` varchar(200) DEFAULT NULL COMMENT '备注',
  `deleted` tinyint DEFAULT 0 COMMENT '删除标志',
  `create_time` datetime DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `update_time` datetime DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  KEY `idx_replenishment_id` (`replenishment_id`),
  KEY `idx_resource_id` (`resource_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='资源补充明细表';

CREATE TABLE IF NOT EXISTS `user` (
  `id` bigint NOT NULL AUTO_INCREMENT COMMENT '用户ID',
  `username` varchar(50) NOT NULL COMMENT '用户名',
  `password` varchar(100) NOT NULL COMMENT '密码(加密)',
  `real_name` varchar(50) DEFAULT NULL COMMENT '真实姓名',
  `role` varchar(50) DEFAULT 'operations' COMMENT '角色',
  `department` varchar(50) DEFAULT '信用卡运营部' COMMENT '部门',
  `phone` varchar(20) DEFAULT NULL COMMENT '电话',
  `email` varchar(100) DEFAULT NULL COMMENT '邮箱',
  `status` tinyint DEFAULT 1 COMMENT '状态',
  `deleted` tinyint DEFAULT 0 COMMENT '删除标志',
  `create_time` datetime DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `update_time` datetime DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_username` (`username`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='用户/员工表';

INSERT IGNORE INTO `benefit_provider`
  (`id`, `provider_code`, `name`, `contact_person`, `phone`, `email`, `address`, `service_rating`, `status`)
VALUES
  (1, 'BP0001', '星享数字权益', '王宁', '021-55501001', 'service@starbenefit.example', '上海市浦东新区', 'A', 1),
  (2, 'BP0002', '云途生活服务', '李晨', '010-55501002', 'ops@cloudtrip.example', '北京市朝阳区', 'A', 1),
  (3, 'BP0003', '惠味餐饮科技', '赵敏', '020-55501003', 'partner@tasteplus.example', '广州市天河区', 'B', 1),
  (4, 'BP0004', '城市出行权益', '陈宇', '0755-55501004', 'support@cityride.example', '深圳市南山区', 'A', 1),
  (5, 'BP0005', '乐购营销互动', '周岚', '0571-55501005', 'business@joypromo.example', '杭州市余杭区', 'B', 1);

INSERT IGNORE INTO `marketing_resource`
  (`id`, `resource_code`, `name`, `model`, `specification`, `unit`, `unit_cost`, `face_value`, `quota_warning_value`, `provider_id`, `category`, `description`)
VALUES
  (1, 'MR1001', '视频会员月卡', 'MONTHLY', '30天有效', '张', 12.80, 25.00, 500, 1, '影音会员', '适用于新户首刷和活跃提升活动'),
  (2, 'MR1002', '音乐会员季卡', 'QUARTERLY', '90天有效', '张', 21.00, 45.00, 300, 1, '影音会员', '适用于年轻客群活跃活动'),
  (3, 'MR2001', '机场贵宾厅权益', 'DOMESTIC', '境内机场单次', '次', 68.00, 120.00, 120, 2, '出行权益', '适用于高净值客户维护'),
  (4, 'MR2002', '网约车立减券', 'RIDE-20', '满30减20', '张', 11.50, 20.00, 800, 4, '出行权益', '适用于月度出行营销活动'),
  (5, 'MR3001', '连锁咖啡兑换券', 'COFFEE-L', '大杯指定饮品', '张', 16.80, 32.00, 600, 3, '餐饮优惠', '适用于消费达标礼活动'),
  (6, 'MR3002', '餐饮满减券', 'FOOD-50', '满100减50', '张', 32.00, 50.00, 400, 3, '餐饮优惠', '适用于周末餐饮促活'),
  (7, 'MR4001', '积分商城通用券', 'POINTS-100', '100元面值', '张', 76.00, 100.00, 200, 5, '积分礼品', '适用于积分兑换和客户补偿'),
  (8, 'MR5001', '新户首刷券包', 'WELCOME', '含3张差异化券', '份', 28.50, 60.00, 1000, 5, '营销券包', '适用于新户首刷转化');

INSERT IGNORE INTO `resource_quota`
  (`resource_id`, `current_quota`, `safety_quota`, `last_replenished_time`, `last_redeemed_time`, `quota_pool`)
VALUES
  (1, 320, 500, '2026-08-20 10:00:00', '2026-08-30 18:20:00', '活跃提升权益池'),
  (2, 680, 300, '2026-08-18 10:00:00', '2026-08-30 16:40:00', '年轻客群权益池'),
  (3, 86, 120, '2026-08-15 11:30:00', '2026-08-29 09:10:00', '高端客户权益池'),
  (4, 1520, 800, '2026-08-22 14:00:00', '2026-08-30 20:05:00', '出行营销权益池'),
  (5, 410, 600, '2026-08-19 15:20:00', '2026-08-30 17:30:00', '消费达标权益池'),
  (6, 760, 400, '2026-08-17 09:30:00', '2026-08-28 19:00:00', '周末促活权益池'),
  (7, 95, 200, '2026-08-12 13:00:00', '2026-08-30 12:10:00', '积分商城权益池'),
  (8, 2450, 1000, '2026-08-25 16:00:00', '2026-08-30 21:00:00', '新户营销权益池');

INSERT IGNORE INTO `resource_replenishment`
  (`id`, `replenishment_number`, `total_amount`, `status`, `replenishment_time`, `expected_activation_date`, `actual_activation_date`, `created_by`, `remark`)
VALUES
  (1, 'BR20260801001', 12800.00, 4, '2026-08-01 09:30:00', '2026-08-03', '2026-08-03', 1, '八月活跃提升活动'),
  (2, 'BR20260808002', 13600.00, 4, '2026-08-08 10:20:00', '2026-08-10', '2026-08-10', 1, '高端客户出行权益补充'),
  (3, 'BR20260815003', 16800.00, 3, '2026-08-15 14:10:00', '2026-08-18', NULL, 1, '消费达标活动资源补充'),
  (4, 'BR20260825004', 22800.00, 2, '2026-08-25 16:40:00', '2026-09-01', NULL, 1, '九月积分商城资源准备');

INSERT IGNORE INTO `replenishment_detail`
  (`replenishment_id`, `resource_id`, `quantity`, `unit_cost`, `remark`)
VALUES
  (1, 1, 1000, 12.80, '视频会员权益'),
  (2, 3, 200, 68.00, '机场贵宾厅权益'),
  (3, 5, 1000, 16.80, '咖啡兑换权益'),
  (4, 7, 300, 76.00, '积分商城通用券');

SET FOREIGN_KEY_CHECKS = 1;
