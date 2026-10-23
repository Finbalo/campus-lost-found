variable "region" {
  type    = string
  default = "eu-west-1"
}

variable "project" {
  type    = string
  default = "campus-lost-found"
}

variable "notify_email" {
  description = "Email that receives possible-match alerts (leave empty to skip). Must confirm the SNS subscription email."
  type        = string
  default     = ""
}
