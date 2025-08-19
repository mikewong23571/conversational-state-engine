# Database Analysis Template

**Database System:** [e.g., SQLite, PostgreSQL]
**Analyst:** [Your name]
**Analysis Date:** [YYYY-MM-DD]
**Files Analyzed:** [List all relevant files with paths]

## Database Overview

### Database Technology
- **Database Type:** [SQLite/PostgreSQL/etc.]
- **Connection Management:** [How connections are handled]
- **Design Specification:** [Reference to design.md section 5]
- **Current Implementation:** [Actual database setup]

### Configuration Analysis
- **Database URL/Location:** [Database file path or connection string]
- **Environment Configuration:** [Environment variables used]
- **Connection Pooling:** [Connection pool configuration if applicable]
- **Performance Settings:** [Database performance configuration]

## Schema Analysis

### Table Structure Compliance

#### Table: [Table Name]
- **File Location:** `path/to/file.py:line_number` (where table is defined/used)
- **Design Specification:** [Expected structure from design.md section 5.1]
- **Actual Implementation:** [Current table structure]
- **Compliance Status:** ✅ Compliant | ⚠️ Partial | ❌ Non-compliant | ❓ Unclear

**Column Analysis:**
| Column Name | Design Type | Actual Type | Constraints | Compliance |
|-------------|-------------|-------------|-------------|------------|
| [column1] | [expected] | [actual] | [constraints] | ✅/⚠️/❌ |
| [column2] | [expected] | [actual] | [constraints] | ✅/⚠️/❌ |

**Missing Columns:** [List any columns from design but not implemented]
**Extra Columns:** [List any columns implemented but not in design]
**Constraint Issues:** [Primary keys, foreign keys, unique constraints issues]

[Repeat for all tables]

### Index Analysis
- **Design Requirements:** [Indexing strategy from design.md]
- **Implemented Indexes:** [Current indexes in database]
- **Missing Indexes:** [Indexes specified in design but not implemented]
- **Performance Impact:** [Analysis of indexing on performance]

### Relationship Analysis
- **Foreign Key Relationships:** [Analysis of table relationships]
- **Referential Integrity:** [How referential integrity is maintained]
- **Cascade Rules:** [Delete/update cascade behavior]
- **Design Compliance:** [How relationships match design specifications]

## Data Model Compliance

### Data Types
- **Type Mapping:** [How application types map to database types]
- **JSON Storage:** [How JSON data is stored and queried]
- **Date/Time Handling:** [Date and timestamp handling approach]
- **Text Storage:** [String and text field handling]

### Validation and Constraints
- **Database-level Validation:** [Constraints enforced at database level]
- **Application-level Validation:** [Validation handled in application code]
- **Data Integrity:** [How data integrity is maintained]
- **Consistency Checks:** [Cross-table consistency validation]

## Transaction Management

### Transaction Implementation
- **Transaction Boundaries:** [How transactions are defined and managed]
- **File Location:** `path/to/file.py:line_number` (transaction handling code)
- **Isolation Levels:** [Transaction isolation settings]
- **Rollback Handling:** [How rollbacks are implemented]

### Atomic Operations
- **Batch Operations:** [How multiple operations are batched]
- **Error Handling:** [Transaction error handling approach]
- **Recovery:** [How system recovers from transaction failures]
- **Design Compliance:** [How implementation matches design requirements]

## Performance Analysis

### Query Performance
- **Query Patterns:** [Common query patterns used]
- **Performance Characteristics:** [Observed query performance]
- **Bottlenecks:** [Identified performance bottlenecks]
- **Optimization Opportunities:** [Potential performance improvements]

### Database Operations
- **Read Performance:** [Read operation performance characteristics]
- **Write Performance:** [Write operation performance characteristics]
- **Bulk Operations:** [Performance of bulk insert/update operations]
- **Connection Performance:** [Connection establishment and management performance]

### Scalability Assessment
- **Current Scale:** [Current database size and load]
- **Design Targets:** [Performance targets from design.md section 12]
- **Scaling Limitations:** [Current scalability constraints]
- **Growth Projections:** [How database will scale with growth]

## Migration and Evolution

### Schema Migration
- **Migration Strategy:** [How schema changes are handled]
- **Version Management:** [Schema version tracking]
- **Migration Scripts:** [Migration script implementation]
- **Rollback Capability:** [Ability to rollback schema changes]

### Data Migration
- **Data Import/Export:** [Data migration capabilities]
- **Format Conversion:** [Data format transformation capabilities]
- **Backup/Restore:** [Backup and restore procedures]
- **Disaster Recovery:** [Disaster recovery planning]

## Security Analysis

### Access Control
- **Authentication:** [Database authentication mechanisms]
- **Authorization:** [Database authorization and permissions]
- **Connection Security:** [Secure connection implementation]
- **Encryption:** [Data encryption at rest and in transit]

### Data Protection
- **Sensitive Data Handling:** [How sensitive data is protected]
- **PII Protection:** [Personal information protection measures]
- **Audit Logging:** [Database operation audit logging]
- **Compliance:** [Security compliance requirements]

## Backup and Recovery

### Backup Strategy
- **Backup Frequency:** [How often backups are performed]
- **Backup Types:** [Full, incremental, differential backups]
- **Storage Location:** [Where backups are stored]
- **Retention Policy:** [How long backups are retained]

### Recovery Procedures
- **Recovery Testing:** [Backup recovery testing procedures]
- **Recovery Time Objectives:** [Target recovery times]
- **Point-in-Time Recovery:** [Ability to recover to specific points in time]
- **Disaster Recovery:** [Disaster recovery capabilities]

## Monitoring and Maintenance

### Database Monitoring
- **Performance Monitoring:** [Database performance monitoring setup]
- **Health Checks:** [Database health monitoring]
- **Alert Configuration:** [Alert setup for database issues]
- **Logging:** [Database operation logging]

### Maintenance Procedures
- **Regular Maintenance:** [Routine database maintenance tasks]
- **Optimization:** [Database optimization procedures]
- **Cleanup:** [Data cleanup and archival procedures]
- **Capacity Planning:** [Database capacity planning]

## Gap Analysis

### Critical Gaps (High Priority)
1. **Gap:** [Description of critical gap]
   - **Impact:** [How this affects database functionality]
   - **Design Reference:** [Relevant design.md section]
   - **Recommended Action:** [What should be done]
   - **Effort Estimate:** [Development effort needed]

### Medium Priority Gaps
1. **Gap:** [Description of gap]
   - **Impact:** [How this affects functionality]
   - **Design Reference:** [Relevant design.md section]
   - **Recommended Action:** [What should be done]
   - **Effort Estimate:** [Development effort needed]

### Low Priority Gaps
1. **Gap:** [Description of gap]
   - **Impact:** [How this affects functionality]
   - **Design Reference:** [Relevant design.md section]
   - **Recommended Action:** [What should be done]
   - **Effort Estimate:** [Development effort needed]

## Testing Analysis

### Database Testing
- **Test Coverage:** [Database testing coverage]
- **Integration Tests:** [Database integration testing]
- **Performance Tests:** [Database performance testing]
- **Migration Tests:** [Schema migration testing]

### Data Integrity Testing
- **Validation Tests:** [Data validation testing]
- **Constraint Tests:** [Database constraint testing]
- **Transaction Tests:** [Transaction integrity testing]
- **Recovery Tests:** [Backup and recovery testing]

## Code Quality Assessment

### Database Code Quality
- **Query Organization:** [How database queries are organized]
- **Code Reusability:** [Reusability of database code]
- **Error Handling:** [Database error handling quality]
- **Documentation:** [Database code documentation quality]

### Best Practices Compliance
- **SQL Best Practices:** [SQL coding best practices adherence]
- **ORM Usage:** [Object-relational mapping usage patterns]
- **Connection Management:** [Database connection best practices]
- **Security Practices:** [Database security best practices]

## Recommendations

### Immediate Actions (0-2 weeks)
1. [Action item with priority and effort estimate]
2. [Action item with priority and effort estimate]

### Short-term Actions (2-8 weeks)
1. [Action item with priority and effort estimate]
2. [Action item with priority and effort estimate]

### Long-term Actions (8+ weeks)
1. [Action item with priority and effort estimate]
2. [Action item with priority and effort estimate]

## Configuration and Deployment

### Database Configuration
- **Environment-specific Configuration:** [Configuration for different environments]
- **Performance Tuning:** [Database performance configuration]
- **Resource Allocation:** [Memory, disk, CPU allocation]
- **Connection Configuration:** [Connection pool and timeout settings]

### Deployment Considerations
- **Database Initialization:** [Database setup and initialization]
- **Schema Deployment:** [Schema deployment procedures]
- **Data Seeding:** [Initial data population procedures]
- **Production Readiness:** [Production deployment considerations]

## Additional Notes

[Any additional observations, concerns, or recommendations not covered in the sections above]

---

**Analysis Complete:** [✅ Yes | ❌ No]
**Reviewed By:** [Reviewer name if applicable]
**Review Date:** [Review date if applicable]
