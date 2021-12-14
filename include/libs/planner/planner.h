/*
 * Copyright (c) 2019 TAOS Data, Inc. <jhtao@taosdata.com>
 *
 * This program is free software: you can use, redistribute, and/or modify
 * it under the terms of the GNU Affero General Public License, version 3
 * or later ("AGPL"), as published by the Free Software Foundation.
 *
 * This program is distributed in the hope that it will be useful, but WITHOUT
 * ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
 * FITNESS FOR A PARTICULAR PURPOSE.
 *
 * You should have received a copy of the GNU Affero General Public License
 * along with this program. If not, see <http://www.gnu.org/licenses/>.
 */

#ifndef _TD_PLANNER_H_
#define _TD_PLANNER_H_

#ifdef __cplusplus
extern "C" {
#endif

#define QUERY_TYPE_MERGE       1
#define QUERY_TYPE_PARTIAL     2

enum OPERATOR_TYPE_E {
  OP_TableScan         = 1,
  OP_DataBlocksOptScan = 2,
  OP_TableSeqScan      = 3,
  OP_TagScan           = 4,
  OP_TableBlockInfoScan= 5,
  OP_Aggregate         = 6,
  OP_Project           = 7,
  OP_Groupby           = 8,
  OP_Limit             = 9,
  OP_SLimit            = 10,
  OP_TimeWindow        = 11,
  OP_SessionWindow     = 12,
  OP_StateWindow       = 22,
  OP_Fill              = 13,
  OP_MultiTableAggregate     = 14,
  OP_MultiTableTimeInterval  = 15,
//  OP_DummyInput        = 16,   //TODO remove it after fully refactor.
//  OP_MultiwayMergeSort = 17,   // multi-way data merge into one input stream.
//  OP_GlobalAggregate   = 18,   // global merge for the multi-way data sources.
  OP_Filter            = 19,
  OP_Distinct          = 20,
  OP_Join              = 21,
  OP_AllTimeWindow     = 23,
  OP_AllMultiTableTimeInterval = 24,
  OP_Order             = 25,
  OP_Exchange          = 26,
};

struct SEpSet;
struct SQueryPlanNode;
struct SQueryPhyPlanNode;
struct SQueryStmtInfo;

typedef struct SSubquery {
  int64_t   queryId;            // the subquery id created by qnode
  int32_t   type;               // QUERY_TYPE_MERGE|QUERY_TYPE_PARTIAL
  int32_t   level;              // the execution level of current subquery, starting from 0.
  SArray   *pUpstream;          // the upstream,from which to fetch the result
  struct SQueryPhyPlanNode *pNode;  // physical plan of current subquery
} SSubquery;

typedef struct SQueryJob {
  SArray  **pSubqueries;
  int32_t   numOfLevels;
  int32_t   currentLevel;
} SQueryJob;


/**
 * Optimize the query execution plan, currently not implement yet.
 * @param pQueryNode
 * @return
 */
int32_t qOptimizeQueryPlan(struct SQueryPlanNode* pQueryNode);

/**
 * Create the query plan according to the bound AST, which is in the form of pQueryInfo
 * @param pQueryInfo
 * @param pQueryNode
 * @return
 */
int32_t qCreateQueryPlan(const struct SQueryStmtInfo* pQueryInfo, struct SQueryPlanNode** pQueryNode);

/**
 * Convert the query plan to string, in order to display it in the shell.
 * @param pQueryNode
 * @return
 */
int32_t qQueryPlanToString(struct SQueryPlanNode* pQueryNode, char** str);

/**
 * Restore the SQL statement according to the logic query plan.
 * @param pQueryNode
 * @param sql
 * @return
 */
int32_t qQueryPlanToSql(struct SQueryPlanNode* pQueryNode, char** sql);

/**
 * Create the physical plan for the query, according to the logic plan.
 * @param pQueryNode
 * @param pPhyNode
 * @return
 */
int32_t qCreatePhysicalPlan(struct SQueryPlanNode* pQueryNode, struct SEpSet* pQnode, struct SQueryPhyPlanNode *pPhyNode);

/**
 * Convert to physical plan to string to enable to print it out in the shell.
 * @param pPhyNode
 * @param str
 * @return
 */
int32_t qPhyPlanToString(struct SQueryPhyPlanNode *pPhyNode, char** str);

/**
 * Destroy the query plan object.
 * @return
 */
void* qDestroyQueryPlan(struct SQueryPlanNode* pQueryNode);

/**
 * Destroy the physical plan.
 * @param pQueryPhyNode
 * @return
 */
void* qDestroyQueryPhyPlan(struct SQueryPhyPlanNode* pQueryPhyNode);

/**
 * Create the query job from the physical execution plan
 * @param pPhyNode
 * @param pJob
 * @return
 */
int32_t qCreateQueryJob(const struct SQueryPhyPlanNode* pPhyNode, struct SQueryJob** pJob);

#ifdef __cplusplus
}
#endif

#endif /*_TD_PLANNER_H_*/