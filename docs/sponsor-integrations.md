# AWS and Bloomerang fit

AWS supports reproducible evidence distribution. Local preparation is implemented; a live upload has not been verified. The benchmark still runs on the same Apple Mac, Luminal supplies the proposer models, and Atlas supplies shared memory. Moving the timing harness to a different machine would create a different experiment.

## AWS evidence distribution

Prepare a content-addressed package without AWS credentials or the optional SDK:

```bash
python scripts/publish_aws.py --run r-20261011-170439
```

This creates `aws-export/<run>/<package-hash>/` with the shared bundle, rendered HTML and SHA-256 manifest. It does not modify submitted artifacts or contact AWS. The package deliberately includes recorded experiment code and prompts already intended for the public submission; do not use this exporter for private customer data.

For an existing bucket configured for private access:

```bash
python -m pip install boto3
python scripts/publish_aws.py --run r-20261011-170439 \
  --upload --bucket YOUR_BUCKET --region YOUR_REGION --profile YOUR_PROFILE \
  --share-link --expires 86400
```

The implementation uses the normal AWS credential chain. Never paste access keys into code or commit a presigned URL. Temporary credentials can make a link expire earlier than the requested lifetime. For a submission that must remain accessible, use the public GitHub report or a separately approved public host instead of relying on an expiring URL.

Uploads verify all local bytes first, use content-addressed keys and conditional writes, and put the manifest last as a completion marker. Repeated uploads check existing object hash metadata. No bucket, ACL, policy, identity or paid compute instance is created. Existing bucket encryption settings apply. IAM access needs `s3:PutObject` and `s3:GetObject` on the chosen `tokenforge/evidence/*` object prefix; a bucket requiring KMS encryption may need its corresponding KMS permissions. Storage and request charges depend on the account's pricing.

The organizer clarification supplied on October 11 specifically mentions AWS's payment system for the AWS track. This S3 archive does not demonstrate that system and does not establish AWS prize eligibility. The exact payment product is unspecified; organizers must identify it before implementation. No AWS payment integration, invoice, sale or letter of intent has been completed. Account registration and other day-of conditions still apply.

References: [S3 conditional uploads](https://docs.aws.amazon.com/boto3/latest/reference/services/s3/client/put_object.html), [presigned URLs](https://docs.aws.amazon.com/AmazonS3/latest/userguide/ShareObjectPreSignedURL.html), [event listing](https://luma.com/compiled-jjvw).

## Bloomerang requires a validated nonprofit workflow

The provided event brief asks for an agent that handles a coordinator's busywork, keeps the coordinator in control, and is demonstrated to the interviewed person. The public event listing describes working, selling and iterating with nonprofits. Neither is satisfied by adding a Bloomerang API logo to an inference optimizer.

No coordinator interview has been completed. There is no validated Bloomerang integration or eligibility claim in this repository.

Use a short interview at the venue:

1. What recurring volunteer task takes the most time this week?
2. Can you show an anonymized input and what a correct completed result looks like?
3. Which decisions must you approve, and can we show you a prototype before submission?

If uncovered shifts are the real problem, a possible extension is to ingest availability and role requirements, propose a schedule, reject availability/qualification/conflict violations, show uncovered shifts and workload balance, and let the coordinator approve an exported schedule. Luminal's competing proposals and Atlas's verified feedback could be reused. This remains a proposed extension until an actual coordinator validates it. Real emails, assignments or CRM writes need explicit authorization.

A Bloomerang API connection is optional unless the coordinator's workflow needs one. The [official API documentation](https://get.bloomerang.co/api/) distinguishes server-to-server REST access from browser forms; credentials belong on the server. API access does not substitute for the interview and demo.
