SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;

CREATE TABLE IF NOT EXISTS `supplier` (
  `id` bigint NOT NULL AUTO_INCREMENT COMMENT '供应商ID',
  `supplier_code` varchar(50) NOT NULL COMMENT '供应商编码',
  `name` varchar(100) NOT NULL COMMENT '供应商名称',
  `contact_person` varchar(50) DEFAULT NULL COMMENT '联系人',
  `phone` varchar(20) DEFAULT NULL COMMENT '联系电话',
  `email` varchar(100) DEFAULT NULL COMMENT '邮箱',
  `address` varchar(200) DEFAULT NULL COMMENT '地址',
  `credit_rating` char(1) DEFAULT 'B' COMMENT '信用评级',
  `status` tinyint DEFAULT 1 COMMENT '合作状态',
  `deleted` tinyint DEFAULT 0 COMMENT '删除标志',
  `create_time` datetime DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `update_time` datetime DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_supplier_code` (`supplier_code`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='供应商表';

CREATE TABLE IF NOT EXISTS `part` (
  `id` bigint NOT NULL AUTO_INCREMENT COMMENT '零部件ID',
  `part_code` varchar(50) NOT NULL COMMENT '零件编码',
  `name` varchar(100) NOT NULL COMMENT '零件名称',
  `model` varchar(100) DEFAULT NULL COMMENT '型号',
  `specification` varchar(200) DEFAULT NULL COMMENT '规格',
  `unit` varchar(20) DEFAULT '个' COMMENT '单位',
  `purchase_price` decimal(10,2) NOT NULL DEFAULT 0.00 COMMENT '采购单价',
  `suggested_retail_price` decimal(10,2) DEFAULT 0.00 COMMENT '建议零售价',
  `stock_warning_value` int DEFAULT 10 COMMENT '库存预警值',
  `supplier_id` bigint DEFAULT NULL COMMENT '供应商ID',
  `category` varchar(50) DEFAULT NULL COMMENT '分类',
  `description` text COMMENT '零件描述',
  `deleted` tinyint DEFAULT 0 COMMENT '删除标志',
  `create_time` datetime DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `update_time` datetime DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_part_code` (`part_code`),
  KEY `idx_supplier_id` (`supplier_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='产品/零部件表';

CREATE TABLE IF NOT EXISTS `inventory` (
  `id` bigint NOT NULL AUTO_INCREMENT COMMENT '库存ID',
  `part_id` bigint NOT NULL COMMENT '零部件ID',
  `current_quantity` int NOT NULL DEFAULT 0 COMMENT '当前库存数量',
  `safety_stock` int DEFAULT 10 COMMENT '安全库存量',
  `last_inbound_time` datetime DEFAULT NULL COMMENT '最近入库时间',
  `last_outbound_time` datetime DEFAULT NULL COMMENT '最近出库时间',
  `warehouse_location` varchar(100) DEFAULT 'A区-1号库' COMMENT '仓库位置',
  `deleted` tinyint DEFAULT 0 COMMENT '删除标志',
  `create_time` datetime DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `update_time` datetime DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_part_id` (`part_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='库存表';

CREATE TABLE IF NOT EXISTS `purchase_order` (
  `id` bigint NOT NULL AUTO_INCREMENT COMMENT '订单ID',
  `order_number` varchar(50) NOT NULL COMMENT '订单编号',
  `total_amount` decimal(12,2) DEFAULT 0.00 COMMENT '订单总金额',
  `status` tinyint DEFAULT 1 COMMENT '订单状态',
  `order_time` datetime DEFAULT CURRENT_TIMESTAMP COMMENT '下单时间',
  `expected_delivery_date` date DEFAULT NULL COMMENT '预计交货日期',
  `actual_delivery_date` date DEFAULT NULL COMMENT '实际交货日期',
  `created_by` bigint DEFAULT NULL COMMENT '创建人ID',
  `remark` varchar(500) DEFAULT NULL COMMENT '备注',
  `deleted` tinyint DEFAULT 0 COMMENT '删除标志',
  `create_time` datetime DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `update_time` datetime DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_order_number` (`order_number`),
  KEY `idx_order_time` (`order_time`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='采购订单表';

CREATE TABLE IF NOT EXISTS `order_detail` (
  `id` bigint NOT NULL AUTO_INCREMENT COMMENT '明细ID',
  `order_id` bigint NOT NULL COMMENT '订单ID',
  `part_id` bigint NOT NULL COMMENT '零部件ID',
  `quantity` int NOT NULL DEFAULT 1 COMMENT '采购数量',
  `unit_price` decimal(10,2) NOT NULL DEFAULT 0.00 COMMENT '采购单价',
  `subtotal` decimal(12,2) GENERATED ALWAYS AS (`quantity` * `unit_price`) STORED COMMENT '小计金额',
  `remark` varchar(200) DEFAULT NULL COMMENT '备注',
  `deleted` tinyint DEFAULT 0 COMMENT '删除标志',
  `create_time` datetime DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `update_time` datetime DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  KEY `idx_order_id` (`order_id`),
  KEY `idx_part_id` (`part_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='订单明细表';

CREATE TABLE IF NOT EXISTS `user` (
  `id` bigint NOT NULL AUTO_INCREMENT COMMENT '用户ID',
  `username` varchar(50) NOT NULL COMMENT '用户名',
  `password` varchar(100) NOT NULL COMMENT '密码(加密)',
  `real_name` varchar(50) DEFAULT NULL COMMENT '真实姓名',
  `role` varchar(50) DEFAULT 'purchase' COMMENT '角色',
  `department` varchar(50) DEFAULT '采购部' COMMENT '部门',
  `phone` varchar(20) DEFAULT NULL COMMENT '电话',
  `email` varchar(100) DEFAULT NULL COMMENT '邮箱',
  `status` tinyint DEFAULT 1 COMMENT '状态',
  `deleted` tinyint DEFAULT 0 COMMENT '删除标志',
  `create_time` datetime DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `update_time` datetime DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_username` (`username`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='用户/员工表';

CREATE TABLE IF NOT EXISTS `customer` (
  `id` bigint NOT NULL AUTO_INCREMENT COMMENT '客户ID',
  `customer_code` varchar(50) NOT NULL COMMENT '客户编码',
  `name` varchar(100) NOT NULL COMMENT '客户名称',
  `contact_person` varchar(50) DEFAULT NULL COMMENT '联系人',
  `phone` varchar(20) DEFAULT NULL COMMENT '联系电话',
  `email` varchar(100) DEFAULT NULL COMMENT '邮箱',
  `address` varchar(200) DEFAULT NULL COMMENT '地址',
  `customer_type` tinyint DEFAULT 1 COMMENT '客户类型',
  `discount_level` tinyint DEFAULT 1 COMMENT '折扣等级',
  `registered_time` datetime DEFAULT CURRENT_TIMESTAMP COMMENT '注册时间',
  `deleted` tinyint DEFAULT 0 COMMENT '删除标志',
  `create_time` datetime DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `update_time` datetime DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_customer_code` (`customer_code`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='客户表';

CREATE TABLE IF NOT EXISTS `logistics` (
  `id` bigint NOT NULL AUTO_INCREMENT COMMENT '物流ID',
  `order_id` bigint NOT NULL COMMENT '订单ID',
  `logistics_company` varchar(100) DEFAULT NULL COMMENT '物流公司',
  `tracking_number` varchar(100) DEFAULT NULL COMMENT '运单号',
  `ship_time` datetime DEFAULT NULL COMMENT '发货时间',
  `estimated_arrival_time` datetime DEFAULT NULL COMMENT '预计到达时间',
  `actual_arrival_time` datetime DEFAULT NULL COMMENT '实际到达时间',
  `status` tinyint DEFAULT 1 COMMENT '物流状态',
  `receiver` varchar(100) DEFAULT NULL COMMENT '收货人',
  `remark` varchar(500) DEFAULT NULL COMMENT '备注',
  `deleted` tinyint DEFAULT 0 COMMENT '删除标志',
  `create_time` datetime DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `update_time` datetime DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  KEY `idx_order_id` (`order_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='物流信息表';

SET FOREIGN_KEY_CHECKS = 1;
