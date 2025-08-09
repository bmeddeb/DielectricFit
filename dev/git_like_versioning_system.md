# Git-Like Versioning System for DielectricFit

## Overview

DielectricFit implements a Git-inspired versioning system for scientific analyses, reports, and documents. This provides full traceability, branching, merging, and collaboration capabilities while maintaining the seamless database integration that users expect.

## Core Concepts

### Version Control Objects (Git-Inspired)

Following Git's object model, we implement four core object types:

1. **Blobs**: Raw content (analysis results, report data, documents)
2. **Trees**: Directory structure and file organization
3. **Commits**: Snapshots with metadata (author, timestamp, message)
4. **Tags**: Named references to specific commits (v1.0, final-report)

### Versioned Entities

The system tracks versions for:

- **Analyses**: Complete analysis workflows and results
- **Reports**: Generated PDF reports and associated data
- **Documents**: Research notes, methodology docs, conclusions
- **Configurations**: Analysis parameters and processing settings

## Data Model Architecture

### Core Versioning Models

```python
class VersionedObject(models.Model):
    """Base class for all versioned objects (blob equivalent)"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    content_type = models.CharField(max_length=50)  # 'analysis', 'report', 'document'
    content_hash = models.CharField(max_length=64, unique=True)  # SHA-256 of content
    size = models.BigIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)
    
    # Polymorphic content storage
    content_json = models.JSONField(blank=True, null=True)  # For structured data
    content_text = models.TextField(blank=True)  # For text documents
    content_binary = models.BinaryField(blank=True, null=True)  # For files
    
    class Meta:
        abstract = False

class Repository(models.Model):
    """Project repository containing versioned objects"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    project = models.OneToOneField(Project, on_delete=models.CASCADE, related_name='repository')
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.project.name} Repository"

class Branch(models.Model):
    """Git-like branches for parallel development"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    repository = models.ForeignKey(Repository, on_delete=models.CASCADE, related_name='branches')
    name = models.CharField(max_length=100)  # main, develop, feature/new-analysis
    head_commit = models.ForeignKey('Commit', on_delete=models.SET_NULL, null=True, related_name='head_of_branches')
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    is_default = models.BooleanField(default=False)
    is_protected = models.BooleanField(default=False)  # Require reviews for changes
    
    class Meta:
        unique_together = [('repository', 'name')]

class Commit(models.Model):
    """Git-like commits representing snapshots in time"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    repository = models.ForeignKey(Repository, on_delete=models.CASCADE, related_name='commits')
    sha = models.CharField(max_length=40, unique=True)  # Git-like SHA hash
    
    # Commit metadata
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name='authored_commits')
    committer = models.ForeignKey(User, on_delete=models.CASCADE, related_name='committed_commits')
    message = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)
    
    # Git-like relationships
    parents = models.ManyToManyField('self', symmetrical=False, blank=True, related_name='children')
    tree = models.ForeignKey('Tree', on_delete=models.CASCADE, related_name='commits')
    
    # Analysis-specific metadata
    analysis_type = models.CharField(max_length=50, blank=True)
    processing_time = models.DurationField(null=True, blank=True)
    dataset_version = models.CharField(max_length=64, blank=True)
    
    class Meta:
        ordering = ['-timestamp']

class Tree(models.Model):
    """Git-like tree representing directory structure"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    sha = models.CharField(max_length=40, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

class TreeEntry(models.Model):
    """Individual entries within a tree"""
    tree = models.ForeignKey(Tree, on_delete=models.CASCADE, related_name='entries')
    name = models.CharField(max_length=255)  # File/folder name
    path = models.CharField(max_length=1000)  # Full path
    mode = models.CharField(max_length=10)  # File permissions (644, 755, etc.)
    object_type = models.CharField(max_length=20)  # 'blob', 'tree'
    object_id = models.UUIDField()  # Points to VersionedObject or Tree
    size = models.BigIntegerField(null=True)

class Tag(models.Model):
    """Named references to specific commits"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    repository = models.ForeignKey(Repository, on_delete=models.CASCADE, related_name='tags')
    name = models.CharField(max_length=100)  # v1.0, final-analysis, published
    commit = models.ForeignKey(Commit, on_delete=models.CASCADE, related_name='tags')
    tagger = models.ForeignKey(User, on_delete=models.CASCADE)
    message = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = [('repository', 'name')]
```

### Specialized Analysis Versioning

```python
class AnalysisVersion(models.Model):
    """Tracks specific analysis workflow versions"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    versioned_object = models.OneToOneField(VersionedObject, on_delete=models.CASCADE)
    
    # Analysis-specific fields
    analysis_type = models.CharField(max_length=50)
    dataset = models.ForeignKey(Dataset, on_delete=models.CASCADE)
    configuration = models.JSONField()  # Parameters used
    results = models.JSONField()  # Analysis outputs
    metadata = models.JSONField(default=dict)
    
    # Performance metrics
    processing_time = models.DurationField()
    memory_usage = models.BigIntegerField(null=True)
    cpu_time = models.DurationField(null=True)
    
    # Quality metrics
    error_metrics = models.JSONField(default=dict)
    convergence_data = models.JSONField(default=dict)
    
    def __str__(self):
        return f"Analysis {self.analysis_type} v{self.versioned_object.content_hash[:8]}"

class ReportVersion(models.Model):
    """Tracks report document versions"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    versioned_object = models.OneToOneField(VersionedObject, on_delete=models.CASCADE)
    
    # Report metadata
    title = models.CharField(max_length=500)
    report_type = models.CharField(max_length=50)  # 'analysis', 'summary', 'publication'
    format = models.CharField(max_length=20)  # 'pdf', 'html', 'docx', 'markdown'
    
    # Dependencies
    based_on_analyses = models.ManyToManyField(AnalysisVersion, blank=True)
    includes_datasets = models.ManyToManyField(Dataset, blank=True)
    
    # Content tracking
    page_count = models.IntegerField(null=True)
    word_count = models.IntegerField(null=True)
    figures_count = models.IntegerField(default=0)
    tables_count = models.IntegerField(default=0)

class DocumentVersion(models.Model):
    """Tracks research document versions (notes, methodology, etc.)"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    versioned_object = models.OneToOneField(VersionedObject, on_delete=models.CASCADE)
    
    document_type = models.CharField(max_length=50)  # 'methodology', 'notes', 'conclusion'
    format = models.CharField(max_length=20)  # 'markdown', 'text', 'html'
    title = models.CharField(max_length=500)
    
    # Collaborative editing
    is_collaborative = models.BooleanField(default=False)
    locked_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    locked_at = models.DateTimeField(null=True, blank=True)
```

## Branching and Merging Strategy

### Branch Types

Following GitHub's model:

1. **main**: Production-ready analyses and reports
2. **develop**: Integration branch for ongoing work
3. **feature/**: Feature development (e.g., `feature/new-fitting-algorithm`)
4. **analysis/**: Specific analysis workflows (e.g., `analysis/cole-cole-optimization`)
5. **report/**: Report development (e.g., `report/quarterly-summary`)
6. **hotfix/**: Critical fixes to published results

### Merge Strategies

```python
class MergeRequest(models.Model):
    """Git-like pull requests for collaborative analysis"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    repository = models.ForeignKey(Repository, on_delete=models.CASCADE)
    
    # Branch information
    source_branch = models.ForeignKey(Branch, on_delete=models.CASCADE, related_name='merge_requests_as_source')
    target_branch = models.ForeignKey(Branch, on_delete=models.CASCADE, related_name='merge_requests_as_target')
    
    # Request metadata
    title = models.CharField(max_length=500)
    description = models.TextField()
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name='merge_requests')
    
    # Status tracking
    status = models.CharField(max_length=20, choices=[
        ('open', 'Open'),
        ('merged', 'Merged'),
        ('closed', 'Closed'),
        ('draft', 'Draft')
    ], default='open')
    
    # Review system
    reviewers = models.ManyToManyField(User, through='MergeRequestReview', related_name='reviewing_merge_requests')
    requires_review = models.BooleanField(default=True)
    
    # Merge information
    merged_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    merged_at = models.DateTimeField(null=True, blank=True)
    merge_commit = models.ForeignKey(Commit, on_delete=models.SET_NULL, null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

class MergeRequestReview(models.Model):
    """Code review system for scientific analyses"""
    merge_request = models.ForeignKey(MergeRequest, on_delete=models.CASCADE)
    reviewer = models.ForeignKey(User, on_delete=models.CASCADE)
    
    status = models.CharField(max_length=20, choices=[
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('changes_requested', 'Changes Requested'),
        ('dismissed', 'Dismissed')
    ])
    
    comment = models.TextField(blank=True)
    reviewed_at = models.DateTimeField(auto_now_add=True)
```

## Version Control Operations

### Core Operations

```python
class VersionControlService:
    """Service class for Git-like operations"""
    
    def commit(self, repository, branch, objects, message, author):
        """Create a new commit with given objects"""
        # Create tree from objects
        tree = self._create_tree(objects)
        
        # Generate commit SHA
        commit_data = f"{tree.sha}{branch.head_commit.sha if branch.head_commit else ''}{message}{author.id}{timezone.now()}"
        sha = hashlib.sha1(commit_data.encode()).hexdigest()
        
        # Create commit
        commit = Commit.objects.create(
            repository=repository,
            sha=sha,
            author=author,
            committer=author,
            message=message,
            tree=tree
        )
        
        # Add parent relationship
        if branch.head_commit:
            commit.parents.add(branch.head_commit)
        
        # Update branch head
        branch.head_commit = commit
        branch.save()
        
        return commit
    
    def create_branch(self, repository, name, from_commit, user):
        """Create a new branch from a commit"""
        return Branch.objects.create(
            repository=repository,
            name=name,
            head_commit=from_commit,
            created_by=user
        )
    
    def merge(self, source_branch, target_branch, user, message):
        """Merge source branch into target branch"""
        # Three-way merge implementation
        common_ancestor = self._find_merge_base(source_branch.head_commit, target_branch.head_commit)
        
        # Create merge commit
        merge_commit = Commit.objects.create(
            repository=source_branch.repository,
            sha=self._generate_merge_sha(source_branch.head_commit, target_branch.head_commit),
            author=user,
            committer=user,
            message=message,
            tree=self._create_merge_tree(source_branch.head_commit, target_branch.head_commit, common_ancestor)
        )
        
        # Add both parents
        merge_commit.parents.add(target_branch.head_commit)
        merge_commit.parents.add(source_branch.head_commit)
        
        # Update target branch
        target_branch.head_commit = merge_commit
        target_branch.save()
        
        return merge_commit
    
    def tag(self, repository, name, commit, user, message=""):
        """Create a tag pointing to a specific commit"""
        return Tag.objects.create(
            repository=repository,
            name=name,
            commit=commit,
            tagger=user,
            message=message
        )
```

## Integration with Existing Models

### Analysis Workflow Integration

```python
class Analysis(models.Model):
    # Existing fields...
    
    # Version control integration
    repository = models.ForeignKey(Repository, on_delete=models.CASCADE, null=True)
    commit = models.ForeignKey(Commit, on_delete=models.SET_NULL, null=True)
    branch = models.ForeignKey(Branch, on_delete=models.SET_NULL, null=True)
    
    def save_as_version(self, message="Auto-save analysis", author=None):
        """Save analysis as a new version"""
        if not self.repository:
            self.repository = self.dataset.project.repository
        
        # Create versioned object
        versioned_obj = VersionedObject.objects.create(
            content_type='analysis',
            content_hash=self._calculate_hash(),
            size=len(str(self.results)),
            content_json={
                'preprocessing_config': self.preprocessing_config.to_dict(),
                'results': self.results,
                'metadata': self.metadata
            }
        )
        
        # Create analysis version
        analysis_version = AnalysisVersion.objects.create(
            versioned_object=versioned_obj,
            analysis_type=self.analysis_type,
            dataset=self.dataset,
            configuration=self.preprocessing_config.to_dict(),
            results=self.results,
            processing_time=self.processing_time
        )
        
        # Commit to repository
        vc_service = VersionControlService()
        commit = vc_service.commit(
            repository=self.repository,
            branch=self.branch or self.repository.branches.filter(is_default=True).first(),
            objects=[versioned_obj],
            message=message,
            author=author or self.created_by
        )
        
        self.commit = commit
        self.save()
        
        return analysis_version
```

## Scientific Workflow Benefits

### Reproducibility
- **Complete traceability** of analysis parameters and results
- **Immutable history** ensuring scientific integrity
- **Rollback capability** to previous analysis states
- **Branch comparison** to evaluate different approaches

### Collaboration
- **Parallel development** of different analysis strategies
- **Merge reviews** for quality control
- **Conflict resolution** for competing hypotheses
- **Shared branches** for team collaboration

### Documentation
- **Version-controlled reports** with full history
- **Linked analyses** showing report dependencies
- **Tag-based releases** for publication milestones
- **Automated documentation** generation from commits

## Usage Examples

### Creating Analysis Branches

```python
# Create feature branch for new analysis
repo = project.repository
main_branch = repo.branches.filter(name='main').first()

feature_branch = vc_service.create_branch(
    repository=repo,
    name='analysis/improved-kramers-kronig',
    from_commit=main_branch.head_commit,
    user=researcher
)

# Perform analysis on feature branch
analysis = Analysis.objects.create(...)
analysis.branch = feature_branch
analysis.save_as_version("Implement improved KK validation", researcher)
```

### Merging Analysis Results

```python
# Create merge request
merge_request = MergeRequest.objects.create(
    repository=repo,
    source_branch=feature_branch,
    target_branch=main_branch,
    title="Improved Kramers-Kronig validation algorithm",
    description="New algorithm shows 15% improvement in accuracy",
    author=researcher,
    requires_review=True
)

# Add reviewers
merge_request.reviewers.add(senior_researcher, lab_director)

# After approval, merge
if merge_request.can_merge():
    merge_commit = vc_service.merge(
        source_branch=feature_branch,
        target_branch=main_branch,
        user=researcher,
        message=f"Merge analysis: {merge_request.title}"
    )
```

### Tagging Publications

```python
# Tag final analysis for publication
publication_commit = main_branch.head_commit
vc_service.tag(
    repository=repo,
    name='publication-v1.0',
    commit=publication_commit,
    user=researcher,
    message="Final analysis results for Nature Materials submission"
)
```

## Implementation Phases

### Phase 1: Core Infrastructure
1. **Basic versioning models** (VersionedObject, Repository, Commit)
2. **Simple commit functionality** for analyses
3. **Linear history** without branching
4. **Basic UI** for version history

### Phase 2: Branching System
1. **Branch model** implementation
2. **Branch creation/switching** functionality
3. **Simple merging** (fast-forward only)
4. **Branch visualization** in UI

### Phase 3: Collaborative Features
1. **Merge request** system
2. **Review workflow** implementation
3. **Three-way merge** algorithm
4. **Conflict resolution** tools

### Phase 4: Advanced Features
1. **Tag system** for releases
2. **Cherry-picking** commits
3. **Rebase functionality** for clean history
4. **Advanced visualization** (network graphs)

This Git-like versioning system transforms DielectricFit into a comprehensive scientific collaboration platform with full traceability, reproducibility, and collaborative development capabilities—all while maintaining seamless database integration and scientific workflow optimization.